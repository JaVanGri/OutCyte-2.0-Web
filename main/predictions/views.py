import threading

import os
import uuid
import logging
import pandas as pd
from django.shortcuts import render
from django.views import View
from django import forms
from predictions.models.outcyte_sp import run_sp
from predictions.models.outcyte_ups import run_ups
from predictions.models.outcyte_ups_v2 import run_ups_v2, read_fasta
from django.core.cache import cache
import oc_settings
logger = logging.getLogger(__name__)


class FastaUploadForm(forms.Form):
    fasta_file = forms.FileField(required=False)
    sequence = forms.CharField(required=False)
    mode = forms.ChoiceField(
        choices=[('standard', 'Standard'), ('standardv2', 'Standard 2.0'), ('sp', 'SP'), ('upsv2', 'UPS 2.0'),
                 ('ups', 'UPS')])


def handle_uploaded_file(f, path):
    with open(path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def find_max_key(result, keys):
    keys = list(set(list(result.keys())).intersection(set(keys)))
    return max(result[keys].to_dict(), key=result.get)


def count_classes(results):
    prediction_counts = {'transmembrane': 0, 'signal_peptide': 0, 'ups': 0, 'intracellular': 0}
    for i in range(len(results)):
        result = results.iloc[i]
        max_key = find_max_key(result, ['transmembrane', 'signal_peptide', 'ups', 'intracellular'])
        prediction_counts[max_key] += 1
    return prediction_counts


def determine_columns_to_remove(mode, form):

    if mode == 'sp':
        colums_to_remove = ['ups']
    elif mode == 'upsv2' or mode == 'ups':
        colums_to_remove = ['transmembrane', 'signal_peptide']
    else:
        colums_to_remove = []

    if not form.cleaned_data.get('fasta_file'):
        colums_to_remove.append('entry')

    return colums_to_remove


def run_standard_mode(file_data):
    results = run_sp(file_data['Entry'], file_data['Sequence'])
    ups_results = run_ups(file_data['Entry'], file_data['Sequence'])
    results['ups'] = (1 - results['transmembrane'] - results['signal_peptide']) * ups_results['ups']
    results['intracellular'] = 1 - results['transmembrane'] - results['signal_peptide'] - results['ups']
    return results


class PredictionView(View):
    form_class = FastaUploadForm
    template_name = 'prediction_form.html'
    results_template = 'prediction_results.html'
    max_file_lines = oc_settings.max_file_lines
    max_file_size = oc_settings.max_file_size * 1024 * 1024
    max_length = oc_settings.max_sequence_length

    alloedChars = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
                   'V', 'W', 'X', 'Y', 'Z']
    device = oc_settings.device
    timeout = oc_settings.time_to_wait_if_calculation_not_ready
    semaphore = threading.Semaphore(oc_settings.maximal_number_parallel_calculations)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        session_key = request.session.session_key
        lock_key = f'lock_{session_key}'

        if cache.get(lock_key):
            error_message = "Status 429: Your last Request is not ready yet."
            return render(request, self.template_name, {'error_message': error_message})

        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            cache.set(lock_key, True, timeout=self.timeout)  # Setze das Lock mit einem Timeout von 5 Minuten
            try:
                mode = form.cleaned_data['mode']
                fasta_file = form.cleaned_data.get('fasta_file')
                sequence = form.cleaned_data.get('sequence')
                file_data, error_message = self.process_input(fasta_file, sequence, mode)
                if error_message:
                    return render(request, self.template_name, {'error_message': error_message})

                results = self.get_predictions(mode, file_data)
                prediction_counts = count_classes(results)
                columns_to_remove = determine_columns_to_remove(mode, form)
                response = render(request, self.results_template, {
                    'prediction_counts': prediction_counts,
                    'columns_to_remove': columns_to_remove,
                    'predictions': results.to_dict(orient='records')
                })
            finally:
                cache.delete(lock_key)  # Entferne das Lock nach der Bearbeitung
            return response
        return render(request, self.template_name, {'error_message': 'Invalid form submission.'})

    def process_input(self, fasta_file, sequence, mode):
        if fasta_file:
            if not fasta_file.name.endswith('.fasta'):
                return None, "Invalid file format. Please upload a FASTA file."
            if fasta_file.size > self.max_file_size:
                return None, "File size exceeds the maximum allowed size of 3 MB."
            temp_file_path = os.path.join('/tmp', f"input_{uuid.uuid4()}.fasta")
            handle_uploaded_file(fasta_file, temp_file_path)
            file_data = read_fasta(temp_file_path)

            file_data = file_data[file_data['Sequence'].str.len() < self.max_length]
            file_data.index = range(len(file_data))

            if mode == 'standard' or mode == 'ups':
                file_data = file_data[file_data['Sequence'].str.len() > 19]
                file_data.index = range(len(file_data))

            file_data['Sequence'] = file_data['Sequence'].str.upper()
            for entry, sequence in file_data[['Entry', 'Sequence']].values:
                if not all(char in self.alloedChars for char in sequence):
                    return None, f"Invalid characters in sequence of {entry}!"

            os.remove(temp_file_path)
            if len(file_data) > self.max_file_lines:
                return None, f"File too large. Only files with fewer than {self.max_file_lines} entries are allowed."

            return file_data, None
        elif sequence:
            sequence = sequence.replace('\r', '')
            sequence = sequence.replace('\n', '')
            sequence = sequence.replace(' ', '')
            sequence = sequence.replace('\t', '')
            if len(sequence) > self.max_length:
                return None, f"Sequence to large. Only Sequences shorter than {self.max_length} allowed."

            if len(sequence) < 20 and (mode == 'standard' or mode == 'ups'):
                return None, f"Old OutCyte-UPS version cannot handle sequence length shorter than 20."

            sequence = sequence.upper()
            if not all(char in self.alloedChars for char in sequence):
                return None, f"Invalid characters!"
            return pd.DataFrame({'Entry': [''], 'Sequence': [sequence]}), None
        else:
            return None, "No input provided."

    def get_predictions(self, mode, file_data):
        if mode == 'standard':
            return run_standard_mode(file_data)
        elif mode == 'sp':
            return run_sp(file_data['Entry'], file_data['Sequence'])
        elif mode == 'ups':
            return run_ups(file_data['Entry'], file_data['Sequence'])

        if len(file_data) > 20:
            with self.semaphore:
                if mode == 'standardv2':
                    return self.run_standard_v2_mode(file_data)
                else:
                    return run_ups_v2(file_data['Entry'], file_data['Sequence'], device=self.device)
        else:
            if mode == 'standardv2':
                return self.run_standard_v2_mode(file_data)
            else:
                return run_ups_v2(file_data['Entry'], file_data['Sequence'], device=self.device)

    def run_standard_v2_mode(self, file_data):
        results = run_sp(file_data['Entry'], file_data['Sequence'])
        ups_results = run_ups_v2(file_data['Entry'], file_data['Sequence'], device=self.device)
        results['ups'] = (1 - results['transmembrane'] - results['signal_peptide']) * ups_results['ups']
        results['intracellular'] = 1 - results['transmembrane'] - results['signal_peptide'] - results['ups']
        return results
