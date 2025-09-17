/**
 * DTI Prediction Page JavaScript
 * Handles single/batch prediction interfaces and real-time updates
 */

class DTIPrediction {
    constructor() {
        this.currentMode = 'single';
        this.predictionActive = false;
        this.currentJob = null;
        this.smilesDrawer = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeSmilesDrawer();
        this.setupFileUpload();
        this.loadPredictionHistory();
    }

    setupEventListeners() {
        // Mode selection
        $('.prediction-mode').on('click', (e) => {
            this.switchMode($(e.currentTarget).data('mode'));
        });

        // Single prediction form
        $('#single-prediction-form').on('submit', (e) => {
            e.preventDefault();
            this.handleSinglePrediction();
        });

        // Batch prediction form
        $('#batch-prediction-form').on('submit', (e) => {
            e.preventDefault();
            this.handleBatchPrediction();
        });

        // SMILES validation
        $('#validate-smiles').on('click', () => {
            this.validateSmiles();
        });

        // Real-time SMILES preview
        $('#smiles-input').on('input', debounce(() => {
            this.updateMoleculePreview();
        }, 500));

        // Cancel prediction
        $('#cancel-prediction').on('click', () => {
            this.cancelPrediction();
        });

        // Download results
        $('#download-results').on('click', () => {
            this.downloadResults();
        });

        // View visualization
        $('#view-visualization').on('click', () => {
            this.openVisualization();
        });
    }

    switchMode(mode) {
        this.currentMode = mode;
        
        // Update UI
        $('.prediction-mode').removeClass('active');
        $(`.prediction-mode[data-mode="${mode}"]`).addClass('active');
        
        // Show/hide panels
        if (mode === 'single') {
            $('#single-prediction').show();
            $('#batch-prediction').hide();
        } else {
            $('#single-prediction').hide();
            $('#batch-prediction').show();
        }
    }

    initializeSmilesDrawer() {
        try {
            this.smilesDrawer = new SmilesDrawer.Drawer({
                width: 300,
                height: 250,
                themes: {
                    light: {
                        C: '#222',
                        O: '#e74c3c',
                        N: '#3498db',
                        S: '#f1c40f',
                        P: '#e67e22'
                    }
                }
            });
        } catch (error) {
            console.warn('SMILES Drawer not available:', error);
        }
    }

    updateMoleculePreview() {
        const smiles = $('#smiles-input').val().trim();
        const previewDiv = $('#molecule-preview');
        
        if (!smiles) {
            previewDiv.html(`
                <div class="text-center text-muted">
                    <i class="fas fa-molecule fa-2x mb-2"></i>
                    <p>Enter SMILES to preview structure</p>
                </div>
            `);
            this.updateCompoundProperties({});
            return;
        }

        if (this.smilesDrawer) {
            try {
                // Clear previous content
                previewDiv.html('<canvas id="molecule-canvas"></canvas>');
                
                // Parse and draw molecule
                SmilesDrawer.parse(smiles, (tree) => {
                    this.smilesDrawer.draw(tree, 'molecule-canvas', 'light', false);
                });

                // Calculate and display properties
                this.calculateMolecularProperties(smiles);
                
            } catch (error) {
                previewDiv.html(`
                    <div class="text-center text-danger">
                        <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                        <p>Invalid SMILES structure</p>
                    </div>
                `);
                this.updateCompoundProperties({});
            }
        } else {
            previewDiv.html(`
                <div class="text-center text-info">
                    <i class="fas fa-info-circle fa-2x mb-2"></i>
                    <p>Structure preview unavailable</p>
                    <small>SMILES: ${smiles}</small>
                </div>
            `);
        }
    }

    calculateMolecularProperties(smiles) {
        // Call backend API to calculate molecular properties
        $.ajax({
            url: '/api/compounds/properties',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ smiles: smiles }),
            success: (data) => {
                this.updateCompoundProperties(data);
            },
            error: () => {
                this.updateCompoundProperties({});
            }
        });
    }

    updateCompoundProperties(properties) {
        const propDiv = $('#compound-properties');
        
        propDiv.html(`
            <div>Molecular Weight: ${properties.molecular_weight || '-'}</div>
            <div>LogP: ${properties.logp || '-'}</div>
            <div>Rotatable Bonds: ${properties.rotatable_bonds || '-'}</div>
        `);
    }

    validateSmiles() {
        const smiles = $('#smiles-input').val().trim();
        const input = $('#smiles-input');
        const feedback = $('#smiles-feedback');
        
        if (!smiles) {
            input.removeClass('is-valid is-invalid');
            return;
        }

        // Call validation API
        $.ajax({
            url: '/api/predict/validate/smiles',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ smiles: smiles }),
            success: (data) => {
                if (data.valid) {
                    input.removeClass('is-invalid').addClass('is-valid');
                    feedback.text('');
                } else {
                    input.removeClass('is-valid').addClass('is-invalid');
                    feedback.text(data.message || 'Invalid SMILES string');
                }
            },
            error: () => {
                input.removeClass('is-valid').addClass('is-invalid');
                feedback.text('Validation failed');
            }
        });
    }

    handleSinglePrediction() {
        const smiles = $('#smiles-input').val().trim();
        const highConfidence = $('#high-confidence').is(':checked');
        const includeStructure = $('#include-structure').is(':checked');

        if (!smiles) {
            this.showAlert('Please enter a SMILES string', 'warning');
            return;
        }

        // Show progress
        this.showProgress();
        this.predictionActive = true;

        // Start prediction
        const data = {
            smiles: smiles,
            high_confidence_only: highConfidence,
            include_structure: includeStructure,
            mode: 'single'
        };

        this.startPrediction(data);
    }

    handleBatchPrediction() {
        const fileInput = $('#file-input')[0];
        const smilesColumn = $('#smiles-column').val();
        const idColumn = $('#id-column').val();

        if (!fileInput.files.length) {
            this.showAlert('Please select a CSV file', 'warning');
            return;
        }

        if (!smilesColumn) {
            this.showAlert('Please select the SMILES column', 'warning');
            return;
        }

        // Show progress
        this.showProgress();
        this.predictionActive = true;

        // Prepare form data
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('smiles_column', smilesColumn);
        formData.append('id_column', idColumn);
        formData.append('mode', 'batch');

        this.startBatchPrediction(formData);
    }

    startPrediction(data) {
        $.ajax({
            url: '/api/predict/single',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: (response) => {
                if (response.success) {
                    this.currentJob = response.job_id;
                    this.pollPredictionStatus();
                } else {
                    this.hideProgress();
                    this.showAlert(response.message || 'Prediction failed', 'danger');
                }
            },
            error: (xhr) => {
                this.hideProgress();
                this.showAlert('Failed to start prediction', 'danger');
            }
        });
    }

    startBatchPrediction(formData) {
        $.ajax({
            url: '/api/predict/batch',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: (response) => {
                if (response.success) {
                    this.currentJob = response.job_id;
                    this.pollPredictionStatus();
                } else {
                    this.hideProgress();
                    this.showAlert(response.message || 'Batch prediction failed', 'danger');
                }
            },
            error: (xhr) => {
                this.hideProgress();
                this.showAlert('Failed to start batch prediction', 'danger');
            }
        });
    }

    pollPredictionStatus() {
        if (!this.currentJob || !this.predictionActive) return;

        $.ajax({
            url: `/api/predict/status/${this.currentJob}`,
            method: 'GET',
            success: (data) => {
                this.updateProgress(data);

                if (data.status === 'completed') {
                    this.predictionCompleted(data);
                } else if (data.status === 'failed') {
                    this.predictionFailed(data);
                } else if (data.status === 'running') {
                    // Continue polling
                    setTimeout(() => this.pollPredictionStatus(), 2000);
                }
            },
            error: () => {
                if (this.predictionActive) {
                    setTimeout(() => this.pollPredictionStatus(), 5000);
                }
            }
        });
    }

    updateProgress(data) {
        const progress = data.progress || 0;
        const processed = data.processed || 0;
        const total = data.total || 0;
        const success = data.success_count || 0;
        const failed = data.failed_count || 0;
        const eta = data.eta || '--:--';

        // Update progress bar
        $('#progress-bar').css('width', `${progress}%`);
        $('#progress-text').text(`${Math.round(progress)}%`);

        // Update counters
        $('#processed-count').text(processed);
        $('#success-count').text(success);
        $('#failed-count').text(failed);
        $('#eta-time').text(eta);

        // Show cancel button if running
        if (data.status === 'running') {
            $('#cancel-prediction').show();
        }
    }

    predictionCompleted(data) {
        this.predictionActive = false;
        this.hideProgress();
        
        // Show results
        this.displayResults(data.results);
        this.addToHistory(data);
        
        this.showAlert('Prediction completed successfully!', 'success');
    }

    predictionFailed(data) {
        this.predictionActive = false;
        this.hideProgress();
        
        this.showAlert(data.error || 'Prediction failed', 'danger');
    }

    cancelPrediction() {
        if (!this.currentJob) return;

        $.ajax({
            url: `/api/predict/cancel/${this.currentJob}`,
            method: 'POST',
            success: () => {
                this.predictionActive = false;
                this.hideProgress();
                this.showAlert('Prediction cancelled', 'info');
            }
        });
    }

    displayResults(results) {
        if (!results || !results.interactions) {
            $('#results-section').hide();
            return;
        }

        const interactions = results.interactions;
        
        // Update summary statistics
        $('#total-interactions').text(interactions.length);
        $('#high-confidence-interactions').text(
            interactions.filter(i => i.score >= 0.95).length
        );
        $('#unique-targets').text(
            new Set(interactions.map(i => i.protein)).size
        );
        $('#avg-score').text(
            (interactions.reduce((sum, i) => sum + i.score, 0) / interactions.length).toFixed(3)
        );

        // Populate results table
        this.populateResultsTable(interactions);
        
        // Show results section
        $('#results-section').show();
        
        // Scroll to results
        $('html, body').animate({
            scrollTop: $('#results-section').offset().top - 100
        }, 500);
    }

    populateResultsTable(interactions) {
        const tbody = $('#results-table tbody');
        tbody.empty();

        interactions.slice(0, 100).forEach((interaction, index) => {
            const confidenceClass = interaction.score >= 0.95 ? 'success' : 
                                  interaction.score >= 0.8 ? 'warning' : 'secondary';
            
            const confidenceText = interaction.score >= 0.95 ? 'High' : 
                                  interaction.score >= 0.8 ? 'Medium' : 'Low';

            const row = `
                <tr>
                    <td>
                        <div class="d-flex align-items-center">
                            <div class="molecule-thumb me-2" data-smiles="${interaction.smiles}"></div>
                            <code class="small">${interaction.smiles.substring(0, 20)}...</code>
                        </div>
                    </td>
                    <td>
                        <a href="/targets/${interaction.protein_id}" target="_blank">
                            ${interaction.protein}
                        </a>
                    </td>
                    <td>
                        <span class="badge bg-light text-dark">${interaction.gene}</span>
                    </td>
                    <td>
                        <span class="fw-bold">${interaction.score.toFixed(4)}</span>
                    </td>
                    <td>
                        <span class="badge bg-${confidenceClass}">${confidenceText}</span>
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" onclick="viewDetails('${interaction.id}')">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-outline-info" onclick="view3DStructure('${interaction.id}')">
                                <i class="fas fa-cube"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });

        // Initialize DataTable for better interaction
        if ($.fn.DataTable.isDataTable('#results-table')) {
            $('#results-table').DataTable().destroy();
        }
        
        $('#results-table').DataTable({
            pageLength: 25,
            order: [[3, 'desc']], // Sort by score
            columnDefs: [
                { orderable: false, targets: [0, 5] } // Disable sorting for compound and actions
            ]
        });
    }

    setupFileUpload() {
        const uploadArea = $('#upload-area');
        const fileInput = $('#file-input');

        // Click to upload
        uploadArea.on('click', () => {
            fileInput.click();
        });

        // Drag and drop
        uploadArea.on('dragover', (e) => {
            e.preventDefault();
            uploadArea.addClass('dragover');
        });

        uploadArea.on('dragleave', () => {
            uploadArea.removeClass('dragover');
        });

        uploadArea.on('drop', (e) => {
            e.preventDefault();
            uploadArea.removeClass('dragover');
            
            const files = e.originalEvent.dataTransfer.files;
            if (files.length > 0) {
                fileInput[0].files = files;
                this.handleFileSelection();
            }
        });

        // File input change
        fileInput.on('change', () => {
            this.handleFileSelection();
        });
    }

    handleFileSelection() {
        const file = $('#file-input')[0].files[0];
        if (!file) return;

        // Validate file
        if (!file.name.toLowerCase().endsWith('.csv')) {
            this.showAlert('Please select a CSV file', 'warning');
            return;
        }

        if (file.size > 10 * 1024 * 1024) { // 10MB limit
            this.showAlert('File size must be less than 10MB', 'warning');
            return;
        }

        // Show file info
        $('#file-name').text(file.name);
        $('#file-size').text(this.formatFileSize(file.size));
        $('#file-info').show();

        // Parse CSV to get columns
        this.parseCSVHeaders(file);
    }

    parseCSVHeaders(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const lines = text.split('\n');
            
            if (lines.length > 0) {
                const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
                this.populateColumnSelectors(headers);
                
                // Estimate compound count
                const compoundCount = Math.max(0, lines.length - 1);
                $('#compound-count').text(compoundCount);
            }
        };
        
        // Read only first few KB to get headers
        reader.readAsText(file.slice(0, 1024));
    }

    populateColumnSelectors(headers) {
        const smilesSelect = $('#smiles-column');
        const idSelect = $('#id-column');
        
        smilesSelect.empty().append('<option value="">Select column...</option>');
        idSelect.empty().append('<option value="">Select column...</option>');
        
        headers.forEach(header => {
            const option = `<option value="${header}">${header}</option>`;
            smilesSelect.append(option);
            idSelect.append(option);
            
            // Auto-select common column names
            if (header.toLowerCase().includes('smiles')) {
                smilesSelect.val(header);
            }
            if (header.toLowerCase().includes('id') || header.toLowerCase().includes('name')) {
                idSelect.val(header);
            }
        });
    }

    downloadResults() {
        if (!this.currentJob) return;

        window.open(`/api/predict/download/${this.currentJob}`, '_blank');
    }

    openVisualization() {
        if (!this.currentJob) return;

        const url = `/visualize/prediction/${this.currentJob}`;
        window.open(url, '_blank');
    }

    addToHistory(data) {
        const history = this.getPredictionHistory();
        
        const entry = {
            id: this.currentJob,
            timestamp: new Date().toISOString(),
            mode: this.currentMode,
            status: 'completed',
            results_count: data.results?.interactions?.length || 0,
            smiles: this.currentMode === 'single' ? $('#smiles-input').val() : null,
            filename: this.currentMode === 'batch' ? $('#file-name').text() : null
        };
        
        history.unshift(entry);
        
        // Keep only last 10 entries
        if (history.length > 10) {
            history.splice(10);
        }
        
        localStorage.setItem('dti_prediction_history', JSON.stringify(history));
        this.displayHistory();
    }

    loadPredictionHistory() {
        this.displayHistory();
    }

    displayHistory() {
        const history = this.getPredictionHistory();
        const container = $('#prediction-history');
        
        if (history.length === 0) {
            container.html(`
                <div class="text-center text-muted py-4">
                    <i class="fas fa-clock fa-2x mb-2"></i>
                    <p>No recent predictions</p>
                </div>
            `);
            return;
        }
        
        const historyHtml = history.map(entry => {
            const date = new Date(entry.timestamp).toLocaleString();
            const modeIcon = entry.mode === 'single' ? 'flask' : 'layer-group';
            const modeClass = entry.mode === 'single' ? 'primary' : 'info';
            
            return `
                <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                    <div>
                        <div class="d-flex align-items-center">
                            <i class="fas fa-${modeIcon} text-${modeClass} me-2"></i>
                            <strong>${entry.mode === 'single' ? 'Single' : 'Batch'} Prediction</strong>
                            <span class="badge bg-success ms-2">${entry.results_count} interactions</span>
                        </div>
                        <small class="text-muted">${date}</small>
                        ${entry.smiles ? `<br><code class="small">${entry.smiles.substring(0, 30)}...</code>` : ''}
                        ${entry.filename ? `<br><span class="small">${entry.filename}</span>` : ''}
                    </div>
                    <div>
                        <button class="btn btn-sm btn-outline-primary" onclick="loadPredictionResults('${entry.id}')">
                            <i class="fas fa-eye me-1"></i>View
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
        container.html(historyHtml);
    }

    getPredictionHistory() {
        try {
            return JSON.parse(localStorage.getItem('dti_prediction_history')) || [];
        } catch {
            return [];
        }
    }

    showProgress() {
        $('.progress-container').show();
        $('#predict-single-btn, #predict-batch-btn').prop('disabled', true);
        
        // Reset progress
        this.updateProgress({
            progress: 0,
            processed: 0,
            success_count: 0,
            failed_count: 0,
            eta: '--:--'
        });
    }

    hideProgress() {
        $('.progress-container').hide();
        $('#predict-single-btn, #predict-batch-btn').prop('disabled', false);
        $('#cancel-prediction').hide();
    }

    showAlert(message, type = 'info') {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Remove existing alerts
        $('.alert').remove();
        
        // Add new alert at top of page
        $('.container-fluid').prepend(alertHtml);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            $('.alert').alert('close');
        }, 5000);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Global functions for table actions
window.viewDetails = function(interactionId) {
    // Open interaction details modal or page
    console.log('View details for:', interactionId);
};

window.view3DStructure = function(interactionId) {
    // Open 3D structure viewer
    console.log('View 3D structure for:', interactionId);
};

window.loadPredictionResults = function(jobId) {
    // Load results from history
    window.location.href = `/predict/results/${jobId}`;
};

// Utility function for debouncing
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize when document is ready
$(document).ready(() => {
    new DTIPrediction();
});