/**
 * Targets Module JavaScript - Handles list and detail page functionality
 */

let targetsTable = null;

// Initialize after page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize appropriate functionality based on current page
    if (document.getElementById('targetsTable')) {
        initializeTargetsListPage();
    }
    
    if (window.targetData) {
        initializeTargetDetailPage();
    }
});

/**
 * Initialize targets list page
 */
function initializeTargetsListPage() {
    initializeDataTable();
    bindListPageEvents();
    
    // Set initial search value
    if (window.pageConfig && window.pageConfig.searchQuery) {
        document.getElementById('searchInput').value = window.pageConfig.searchQuery;
    }
}

/**
 * Initialize DataTables with fixed pagination and data loading
 */
function initializeDataTable() {
    targetsTable = $('#targetsTable').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            // Fixed: Use the correct endpoint that returns DataTables format
            url: '/targets/api/list',
            type: 'GET',
            data: function(d) {
                // Add custom search parameter
                d.search_custom = document.getElementById('searchInput').value || null;
                return d;
            },
            error: function(xhr, error, thrown) {
                console.error('DataTable error:', error);
                Utils.showToast('Failed to load targets data', 'error');
            }
        },
        columns: [
            {
                data: 'gene_name',
                title: 'Gene Name',
                render: function(data, type, row) {
                    const geneName = data || row.gene_symbol || 'Unknown';
                    return `<span class="fw-medium">${geneName}</span>`;
                }
            },
            {
                data: 'gene_symbol',
                title: 'Gene Symbol',
                width: '120px',
                render: function(data) {
                    return data ? `<code class="text-primary">${data}</code>` : '<span class="text-muted">N/A</span>';
                }
            },
            {
                data: 'prediction_count',
                title: 'Prediction Count',
                width: '140px',
                render: function(data) {
                    if (!data || data === 0) {
                        return '<span class="text-muted">-</span>';
                    }
                    let badgeClass = 'secondary';
                    if (data >= 50) badgeClass = 'success';
                    else if (data >= 20) badgeClass = 'info';
                    else if (data >= 10) badgeClass = 'warning';
                    
                    return `<span class="badge bg-${badgeClass} fs-6">${data}</span>`;
                }
            },
            {
                data: 'avg_score',
                title: 'Average Score',
                width: '140px',
                render: function(data) {
                    if (!data || data === 0) {
                        return '<span class="text-muted">-</span>';
                    }
                    const score = parseFloat(data);
                    let scoreClass = 'secondary';
                    if (score >= 0.95) scoreClass = 'success';
                    else if (score >= 0.90) scoreClass = 'warning';
                    else if (score >= 0.80) scoreClass = 'info';
                    
                    return `<span class="badge bg-${scoreClass} fs-6">${score.toFixed(4)}</span>`;
                }
            },
            {
                data: 'uniprot_id',
                title: 'UniProt ID',
                width: '120px',
                render: function(data) {
                    if (!data) return '<span class="text-muted">N/A</span>';
                    return `<a href="https://www.uniprot.org/uniprot/${data}" target="_blank" class="text-decoration-none">
                        ${data} <i class="fas fa-external-link-alt small text-muted"></i>
                    </a>`;
                }
            },
            {
                data: null,
                title: 'Actions',
                orderable: false,
                width: '120px',
                render: function(data, type, row) {
                    const geneName = row.gene_symbol || row.gene_name || 'unknown';
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" onclick="viewTarget('${geneName}')" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-outline-success" onclick="viewCompounds('${geneName}')" title="Related Compounds">
                                <i class="fas fa-atom"></i>
                            </button>
                        </div>
                    `;
                }
            }
        ],
        pageLength: 20,
        lengthMenu: [[10, 20, 50, 100], [10, 20, 50, 100]],
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/en.json',
            processing: "Loading targets...",
            search: "Search targets:",
            lengthMenu: "Show _MENU_ targets per page",
            info: "Showing _START_ to _END_ of _TOTAL_ targets",
            infoEmpty: "No targets found",
            infoFiltered: "(filtered from _MAX_ total targets)",
            paginate: {
                first: "First",
                last: "Last",
                next: "Next",
                previous: "Previous"
            }
        },
        order: [[2, 'desc']], // Sort by prediction count descending
        responsive: true
    });
}

/**
 * Bind list page events
 */
function bindListPageEvents() {
    // Search input enter key
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            targetsTable.ajax.reload();
        }
    });
    
    // Real-time search (debounced)
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            targetsTable.ajax.reload();
        }, 500);
    });
    
    // Clear search button
    document.getElementById('clearSearch').addEventListener('click', function() {
        document.getElementById('searchInput').value = '';
        targetsTable.ajax.reload();
    });
}

/**
 * View target details
 */
function viewTarget(geneName) {
    window.location.href = `/targets/${encodeURIComponent(geneName)}`;
}

/**
 * View related compounds
 */
function viewCompounds(geneName) {
    window.location.href = `/targets/${encodeURIComponent(geneName)}#compounds`;
}

/**
 * Initialize target detail page
 */
function initializeTargetDetailPage() {
    loadCompoundsData();
}

/**
 * Load related compounds data
 */
async function loadCompoundsData() {
    const container = document.getElementById('compoundsContainer');
    const countBadge = document.getElementById('compoundCount');
    
    if (!container || !window.targetData) return;
    
    try {
        let compounds = [];
        
        // If data is already available, use it directly
        if (window.targetData.associated_compounds) {
            compounds = window.targetData.associated_compounds;
        } else {
            // Otherwise get data through API
            const geneName = window.targetData.gene_symbol || window.targetData.gene_name;
            const response = await apiClient.get(`/targets/${encodeURIComponent(geneName)}/compounds`);
            compounds = response.data.compounds || [];
        }
        
        displayCompounds(compounds);
        
    } catch (error) {
        console.error('Error loading compounds:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load related compounds
            </div>
        `;
        countBadge.textContent = '0';
    }
}

/**
 * Display related compounds
 */
function displayCompounds(compounds) {
    const container = document.getElementById('compoundsContainer');
    const countBadge = document.getElementById('compoundCount');
    
    if (!compounds || compounds.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-info-circle fa-2x mb-3"></i>
                <p>No related compounds data available</p>
            </div>
        `;
        countBadge.textContent = '0';
        return;
    }
    
    countBadge.textContent = compounds.length;
    
    // Sort by score and take top 20
    const sortedCompounds = compounds.sort((a, b) => (b.score || 0) - (a.score || 0));
    const displayCompounds = sortedCompounds.slice(0, 20);
    
    // Generate compounds list HTML
    let compoundsHtml = displayCompounds.map(compound => {
        const score = compound.score || 0;
        const scoreClass = score >= 0.95 ? 'success' : score >= 0.90 ? 'warning' : 'secondary';
        const compoundName = compound.chinese_name || compound.Name || `ID: ${compound.compound_id}`;
        
        return `
            <div class="border-bottom pb-2 mb-2">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <a href="/compounds/${compound.global_id || compound.compound_id}" 
                               class="text-decoration-none" target="_blank">
                                ${compoundName}
                            </a>
                        </h6>
                        <small class="text-muted">
                            Type: ${compound.compound_type || 'N/A'}
                            ${compound.molecular_formula ? ` • Formula: ${compound.molecular_formula}` : ''}
                        </small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-${scoreClass}">
                            ${score.toFixed(4)}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Add "show more" note if there are more compounds
    if (sortedCompounds.length > 20) {
        compoundsHtml += `
            <div class="text-center mt-3">
                <small class="text-muted">
                    Showing top 20 high-scoring compounds of ${sortedCompounds.length} total compounds
                </small>
            </div>
        `;
    }
    
    container.innerHTML = compoundsHtml;
}