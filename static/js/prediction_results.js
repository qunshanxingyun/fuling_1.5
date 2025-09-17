/**
 * Prediction Results Page JavaScript
 * Handles results display, visualization, and interaction
 */

class PredictionResults {
    constructor() {
        this.jobId = window.pageConfig?.jobId;
        this.apiBaseUrl = window.pageConfig?.apiBaseUrl || '/api/predict';
        this.results = null;
        this.charts = {};
        
        this.init();
    }

    init() {
        if (!this.jobId) {
            this.showError('No job ID provided');
            return;
        }
        
        this.setupEventListeners();
        this.loadResults();
    }

    setupEventListeners() {
        // Download buttons
        $('#download-csv').on('click', () => this.downloadResults('csv'));
        $('#download-excel').on('click', () => this.downloadResults('excel'));
        $('#share-results').on('click', () => this.shareResults());
        
        // Table controls
        $('#table-search').on('input', () => this.filterTable());
        $('#confidence-filter').on('change', () => this.filterTable());
        $('#reset-filters').on('click', () => this.resetFilters());
        
        // Tab switching
        $('#analysis-tabs button[data-bs-toggle="tab"]').on('shown.bs.tab', (e) => {
            this.handleTabSwitch(e.target.id);
        });
        
        // Network controls
        $('#reset-network').on('click', () => this.resetNetworkView());
        $('#export-network').on('click', () => this.exportNetwork());
        
        // New prediction button
        $('#new-prediction').on('click', () => {
            window.location.href = '/predict';
        });
    }

    async loadResults() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/results/${this.jobId}`);
            const data = await response.json();
            
            if (data.success && data.results) {
                this.results = data.results;
                this.displayResults();
                this.hideLoading();
            } else {
                this.showError('Results not found or unavailable');
            }
        } catch (error) {
            console.error('Error loading results:', error);
            this.showError('Failed to load prediction results');
        }
    }

    displayResults() {
        if (!this.results || !this.results.interactions) {
            this.showError('No interaction data available');
            return;
        }

        const interactions = this.results.interactions;
        
        // Update summary statistics
        this.updateSummaryStats(interactions);
        
        // Populate interactions table
        this.populateInteractionsTable(interactions);
        
        // Set completion time
        $('#completion-time').text(new Date().toLocaleString());
    }

    updateSummaryStats(interactions) {
        const totalInteractions = interactions.length;
        const highConfidence = interactions.filter(i => i.score >= 0.95).length;
        const uniqueTargets = new Set(interactions.map(i => i.protein)).size;
        const avgScore = totalInteractions > 0 ? 
            (interactions.reduce((sum, i) => sum + i.score, 0) / totalInteractions).toFixed(3) : '0.000';

        $('#total-interactions').text(totalInteractions.toLocaleString());
        $('#high-confidence').text(highConfidence.toLocaleString());
        $('#unique-targets').text(uniqueTargets.toLocaleString());
        $('#avg-score').text(avgScore);
    }

    populateInteractionsTable(interactions) {
        const tbody = $('#interactions-table tbody');
        tbody.empty();

        // Sort by score (highest first)
        const sortedInteractions = [...interactions].sort((a, b) => b.score - a.score);

        sortedInteractions.forEach((interaction, index) => {
            const confidenceLevel = this.getConfidenceLevel(interaction.score);
            const confidenceClass = this.getConfidenceClass(interaction.score);
            
            const row = `
                <tr data-score="${interaction.score}" data-confidence="${confidenceLevel.toLowerCase()}">
                    <td>
                        <div class="d-flex align-items-center">
                            <code class="small text-truncate" style="max-width: 200px;" title="${interaction.smiles}">
                                ${interaction.smiles}
                            </code>
                        </div>
                    </td>
                    <td>
                        <div>
                            <span class="fw-medium">${interaction.protein}</span>
                        </div>
                    </td>
                    <td>
                        <span class="badge bg-light text-dark">${interaction.gene}</span>
                    </td>
                    <td>
                        <span class="fw-bold">${interaction.score.toFixed(4)}</span>
                    </td>
                    <td>
                        <span class="badge bg-${confidenceClass}">${confidenceLevel}</span>
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" onclick="viewInteractionDetails('${interaction.id || index}')">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-outline-info" onclick="view3DStructure('${interaction.id || index}')">
                                <i class="fas fa-cube"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });

        // Initialize DataTable
        this.initializeDataTable();
    }

    initializeDataTable() {
        // Destroy existing DataTable if it exists
        if ($.fn.DataTable.isDataTable('#interactions-table')) {
            $('#interactions-table').DataTable().destroy();
        }
        
        $('#interactions-table').DataTable({
            pageLength: 25,
            order: [[3, 'desc']], // Sort by score
            columnDefs: [
                { orderable: false, targets: [0, 5] }, // Disable sorting for compound and actions
                { searchable: false, targets: [5] } // Disable search for actions column
            ],
            language: {
                search: "", // Remove default search label
                searchPlaceholder: "Search interactions..."
            },
            dom: '<"row"<"col-sm-6"l><"col-sm-6"f>>rtip'
        });
    }

    getConfidenceLevel(score) {
        if (score >= 0.95) return 'High';
        if (score >= 0.8) return 'Medium';
        return 'Low';
    }

    getConfidenceClass(score) {
        if (score >= 0.95) return 'success';
        if (score >= 0.8) return 'warning';
        return 'secondary';
    }

    filterTable() {
        const searchTerm = $('#table-search').val().toLowerCase();
        const confidenceFilter = $('#confidence-filter').val();
        
        const table = $('#interactions-table').DataTable();
        
        // Apply confidence filter
        if (confidenceFilter) {
            table.column(4).search(confidenceFilter, false, false);
        } else {
            table.column(4).search('');
        }
        
        // Apply text search
        table.search(searchTerm);
        
        table.draw();
    }

    resetFilters() {
        $('#table-search').val('');
        $('#confidence-filter').val('');
        
        const table = $('#interactions-table').DataTable();
        table.search('').columns().search('').draw();
    }

    handleTabSwitch(tabId) {
        switch(tabId) {
            case 'visualization-tab':
                this.initializeVisualizations();
                break;
            case 'network-tab':
                this.initializeNetworkView();
                break;
            case 'analysis-tab':
                this.initializeAnalysis();
                break;
        }
    }

    initializeVisualizations() {
        if (!this.results || this.charts.initialized) return;
        
        // Score distribution histogram
        this.createScoreHistogram();
        
        // Top targets chart
        this.createTopTargetsChart();
        
        this.charts.initialized = true;
    }

    createScoreHistogram() {
        const ctx = document.getElementById('score-histogram');
        if (!ctx) return;

        const scores = this.results.interactions.map(i => i.score);
        const bins = this.createHistogramBins(scores, 20);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: bins.labels,
                datasets: [{
                    label: 'Number of Interactions',
                    data: bins.counts,
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Frequency'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Prediction Score'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Distribution of Prediction Scores'
                    }
                }
            }
        });
    }

    createTopTargetsChart() {
        const ctx = document.getElementById('targets-chart');
        if (!ctx) return;

        // Count interactions per target
        const targetCounts = {};
        this.results.interactions.forEach(i => {
            targetCounts[i.protein] = (targetCounts[i.protein] || 0) + 1;
        });

        // Get top 10 targets
        const topTargets = Object.entries(targetCounts)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10);

        new Chart(ctx, {
            type: 'horizontalBar',
            data: {
                labels: topTargets.map(([name]) => name.length > 20 ? name.substring(0, 20) + '...' : name),
                datasets: [{
                    label: 'Number of Interactions',
                    data: topTargets.map(([,count]) => count),
                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Interactions'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Top 10 Target Proteins'
                    }
                }
            }
        });
    }

    createHistogramBins(data, numBins) {
        const min = Math.min(...data);
        const max = Math.max(...data);
        const binWidth = (max - min) / numBins;
        
        const bins = Array(numBins).fill(0);
        const labels = [];
        
        for (let i = 0; i < numBins; i++) {
            const binStart = min + i * binWidth;
            const binEnd = min + (i + 1) * binWidth;
            labels.push(`${binStart.toFixed(2)}-${binEnd.toFixed(2)}`);
        }
        
        data.forEach(value => {
            const binIndex = Math.min(Math.floor((value - min) / binWidth), numBins - 1);
            bins[binIndex]++;
        });
        
        return { labels, counts: bins };
    }

    initializeNetworkView() {
        // Placeholder for network visualization
        const container = $('#network-container');
        container.html(`
            <div class="text-center py-5">
                <i class="fas fa-project-diagram fa-3x text-muted mb-3"></i>
                <h5>Network View</h5>
                <p class="text-muted">Interactive network visualization will be implemented here</p>
            </div>
        `);
    }

    initializeAnalysis() {
        // Placeholder for advanced analysis
        $('#pathway-analysis').html(`
            <div class="text-center py-3">
                <i class="fas fa-chart-line fa-2x text-muted mb-2"></i>
                <p class="text-muted">Pathway enrichment analysis coming soon</p>
            </div>
        `);
        
        $('#target-families').html(`
            <div class="text-center py-3">
                <i class="fas fa-sitemap fa-2x text-muted mb-2"></i>
                <p class="text-muted">Target family analysis coming soon</p>
            </div>
        `);
    }

    downloadResults(format) {
        if (format === 'csv') {
            window.open(`${this.apiBaseUrl}/download/${this.jobId}`, '_blank');
        } else {
            this.showToast('Excel download coming soon', 'info');
        }
    }

    shareResults() {
        const url = window.location.href;
        if (navigator.share) {
            navigator.share({
                title: 'Prediction Results',
                url: url
            });
        } else {
            // Fallback to clipboard
            navigator.clipboard.writeText(url).then(() => {
                this.showToast('Results URL copied to clipboard', 'success');
            });
        }
    }

    resetNetworkView() {
        this.showToast('Network view reset', 'info');
    }

    exportNetwork() {
        this.showToast('Network export coming soon', 'info');
    }

    hideLoading() {
        $('#loading-state').hide();
        $('#main-content').show();
    }

    showError(message) {
        $('#loading-state').html(`
            <div class="text-center py-5">
                <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                <h5>Error Loading Results</h5>
                <p class="text-muted">${message}</p>
                <a href="/predict" class="btn btn-primary">
                    <i class="fas fa-arrow-left me-2"></i>Back to Prediction
                </a>
            </div>
        `);
    }

    showToast(message, type = 'info') {
        // Simple toast notification
        const toastHtml = `
            <div class="toast show" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 1055;">
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        $('body').append(toastHtml);
        setTimeout(() => $('.toast').remove(), 3000);
    }
}

// Global functions for table actions
window.viewInteractionDetails = function(interactionId) {
    console.log('View details for:', interactionId);
    // Implement interaction details modal
};

window.view3DStructure = function(interactionId) {
    console.log('View 3D structure for:', interactionId);
    // Implement 3D structure viewer
};

// Initialize when document is ready
$(document).ready(() => {
    new PredictionResults();
});