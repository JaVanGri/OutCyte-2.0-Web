# outcyte_settings.py
# This file contains configurable parameters for the OutCyte 2.0 application.

# Maximum number of proteins that can be included in a single input file.
max_file_lines = 10000  # Maximal number of proteins in one file.

# Maximum allowable file size for the input file in bytes (3 MB).
max_file_size = 3   # Maximal file size (3MB).

# Maximum length of a protein sequence that can be processed.
max_sequence_length = 2700  # Maximal sequence length of a protein.

# Time in seconds to wait before submitting the next file if the previous submission is still processing.
time_to_wait_if_calculation_not_ready = 1  # Use 1 second for local operations.

# Maximum number of parallel calculations allowed for UPS v2 predictions.
maximal_number_parallel_calculations = 1  # Limit to 1 for controlled resource usage.

# Specify the computation device to be used: 'cpu' for CPU or 'cuda' for NVIDIA GPUs.
device = 'cpu'  # Default is CPU; change to 'cuda' if GPU is available and supported.

# Maximum number of simultaneous requests allowed from different clients.
max_number_requests_different_clients = 5  # Limits the number of concurrent client interactions.