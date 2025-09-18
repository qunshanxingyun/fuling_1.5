/**
 * Compounds Module JavaScript - Handles list and detail page functionality
 */

let compoundsTable = null;

// Initialize after page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize appropriate functionality based on current page
    if (document.getElementById('compoundsTable')) {
        initializeCompoundsListPage();
    }
    
    if (window.compoundData) {
        initializeCompoundDetailPage();
    }
});

/**
 * Initialize compounds list page
 */
function initializeCompoundsListPage() {
    initializeDataTable();
    bindListPageEvents();
    
    // Set initial filter values
    if (window.pageConfig) {
        if (window.pageConfig.compoundType && window.pageConfig.compoundType !== 'all') {
            document.getElementById('typeFilter').value = window.pageConfig.compoundType;
        }
        if (window.pageConfig.searchQuery) {
            document.getElementById('searchInput').value = window.pageConfig.searchQuery;
        }
    }
}

/**
 * Initialize DataTables with fixed pagination
 */
function initializeDataTable() {
    compoundsTable = $('#compoundsTable').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            // Fixed: Use the correct endpoint that returns DataTables format
            url: '/compounds/api/list',
            type: 'GET',
            data: function(d) {
                // Add custom filter parameters to DataTables request
                d.compound_type = document.getElementById('typeFilter').value !== 'all' ? 
                                 document.getElementById('typeFilter').value : null;
                d.search_custom = document.getElementById('searchInput').value || null;
                return d;
            },
            error: function(xhr, error, thrown) {
                console.error('DataTable error:', error);
                Utils.showToast('Failed to load data', 'error');
            }
        },
        columns: [
            {
                data: 'global_id',
                title: 'ID',
                width: '80px',
                render: function(data) {
                    return `<strong>${data}</strong>`;
                }
            },
            {
                data: 'chinese_name',
                title: 'Chinese Name',
                render: function(data) {
                    return data || '<span class="text-muted">Unnamed</span>';
                }
            },
            {
                data: 'Name',
                title: 'English Name',
                render: function(data) {
                    return data || '<span class="text-muted">Unnamed</span>';
                }
            },
            {
                data: 'compound_type',
                title: 'Type',
                width: '120px',
                render: function(data) {
                    const types = {
                        '挥发油': { label: 'Essential Oils', color: 'success' },
                        '三萜': { label: 'Triterpenes', color: 'info' },
                        '甾醇': { label: 'Sterols', color: 'warning' }
                    };
                    const type = types[data] || { label: data, color: 'secondary' };
                    return `<span class="badge bg-${type.color}">${type.label}</span>`;
                }
            },
            {
                data: 'Molecular_Formula',
                title: 'Molecular Formula',
                render: function(data) {
                    return data ? `<code>${data}</code>` : '<span class="text-muted">N/A</span>';
                }
            },
            {
                data: 'Molecular_Weight',
                title: 'Molecular Weight',
                width: '140px',
                render: function(data) {
                    return data ? `${parseFloat(data).toFixed(2)} g/mol` : '<span class="text-muted">N/A</span>';
                }
            },
            {
                data: null,
                title: 'Actions',
                orderable: false,
                width: '100px',
                render: function(data, type, row) {
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" onclick="viewCompound(${row.global_id})" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-outline-success" onclick="viewTargets(${row.global_id})" title="Predicted Targets">
                                <i class="fas fa-bullseye"></i>
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
            processing: "Loading compounds...",
            search: "Search compounds:",
            lengthMenu: "Show _MENU_ compounds per page",
            info: "Showing _START_ to _END_ of _TOTAL_ compounds",
            infoEmpty: "No compounds found",
            infoFiltered: "(filtered from _MAX_ total compounds)",
            paginate: {
                first: "First",
                last: "Last",
                next: "Next",
                previous: "Previous"
            }
        },
        order: [[0, 'asc']],
        responsive: true
    });
}

/**
 * Bind list page events
 */
function bindListPageEvents() {
    // Filter changes - reload table when type filter changes
    document.getElementById('typeFilter').addEventListener('change', function() {
        compoundsTable.ajax.reload();
    });
    
    // Search input enter key
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            compoundsTable.ajax.reload();
        }
    });
    
    // Real-time search (debounced)
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            compoundsTable.ajax.reload();
        }, 500);
    });
}

/**
 * View compound details
 */
function viewCompound(compoundId) {
    window.location.href = `/compounds/${compoundId}`;
}

/**
 * View predicted targets
 */
function viewTargets(compoundId) {
    window.location.href = `/compounds/${compoundId}#targets`;
}

/**
 * Initialize compound detail page
 */
function initializeCompoundDetailPage() {
    loadTargetsData();
}

/**
 * Load 2D molecular structure
 */
function loadMoleculeStructure() {
    const viewer = document.getElementById('moleculeViewer');
    if (!viewer || !window.compoundData || !window.compoundData.SMILES) {
        viewer.innerHTML = '<p class="text-center text-muted">Unable to load structure: Missing SMILES data.</p>';
        return;
    }

    // Create a Canvas element
    const canvas = document.createElement('canvas');
    canvas.id = 'smiles-canvas';
    viewer.innerHTML = ''; // Clear placeholder
    viewer.appendChild(canvas);

    try {
        // Initialize SmilesDrawer
        const drawer = new SmilesDrawer.Drawer({
            width: viewer.clientWidth || 400,
            height: 350,
            bondThickness: 2,
            bondLength: 15
        });

        // Draw structure
        SmilesDrawer.parse(window.compoundData.SMILES, function(tree) {
            drawer.draw(tree, 'smiles-canvas', 'light', false);
        }, function(err) {
            console.error("SMILES parsing error:", err);
            viewer.innerHTML = '<p class="text-center text-danger">Failed to parse SMILES structure.</p>';
        });
    } catch (error) {
        console.error("SmilesDrawer error:", error);
        viewer.innerHTML = '<p class="text-center text-warning">Molecular visualization unavailable.</p>';
    }
}

/**
 * Show full InChI
 */
function showFullInChI() {
    if (window.compoundData && window.compoundData.InChI) {
        document.getElementById('fullInchiText').value = window.compoundData.InChI;
        const inchiModal = new bootstrap.Modal(document.getElementById('inchiModal'));
        inchiModal.show();
    }
}

/**
 * Load predicted targets data with pagination
 */
async function loadTargetsData(page = 1, pageSize = 10, sortBy = 'score') {
    const container = document.getElementById('targetsContainer');
    
    if (!container || !window.compoundData) return;
    
    try {
        // Show loading state
        container.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 text-muted">Loading predicted targets...</p>
            </div>
        `;
        
        // Fetch paginated data from API
        const response = await apiClient.get(`/compounds/${window.compoundData.global_id}/targets`, {
            page: page,
            page_size: pageSize,
            sort_by: sortBy
        });
        
        const targets = response.data.targets || [];
        const statistics = response.data.statistics || {};
        const pagination = response.data.pagination || {};
        
        displayTargets(targets, statistics, pagination, page, pageSize);
        
    } catch (error) {
        console.error('Error loading targets:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load predicted targets
            </div>
        `;
    }
}

/**
 * Display predicted targets with pagination
 */
function displayTargets(targets, statistics, pagination, currentPage, pageSize) {
    const container = document.getElementById('targetsContainer');
    
    if (!targets || targets.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-info-circle fa-2x mb-3"></i>
                <p>No predicted targets available</p>
            </div>
        `;
        return;
    }
    
    // Sort targets by score (highest first)
    const sortedTargets = targets.sort((a, b) => (b.score || 0) - (a.score || 0));
    
    // Build targets list HTML
    let targetsHtml = `
        <div class="mb-3">
            <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted">
                    Showing ${((currentPage - 1) * pageSize) + 1}-${Math.min(currentPage * pageSize, pagination.total || 0)} 
                    of ${pagination.total || 0} targets
                </small>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary btn-sm" onclick="sortTargets('score')" title="Sort by Score">
                        <i class="fas fa-sort-numeric-down"></i>
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" onclick="sortTargets('name')" title="Sort by Name">
                        <i class="fas fa-sort-alpha-down"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    targetsHtml += sortedTargets.map(target => {
        const score = target.score || 0;
        const scoreClass = score >= 0.95 ? 'success' : score >= 0.90 ? 'warning' : 'secondary';
        const geneName = target.gene_name || target.From || 'Unknown';
        const geneSymbol = target.gene_symbol || '';
        
        return `
            <div class="border-bottom pb-2 mb-2 target-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <a href="/targets/${encodeURIComponent(geneSymbol || geneName)}" 
                               class="text-decoration-none" target="_blank" title="View target details">
                                ${geneName}
                            </a>
                        </h6>
                        ${geneSymbol && geneSymbol !== geneName ? 
                          `<small class="text-muted">Gene Symbol: <code>${geneSymbol}</code></small>` : ''}
                    </div>
                    <div class="text-end">
                        <span class="badge bg-${scoreClass}" title="Prediction Score">
                            ${score.toFixed(4)}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Add pagination controls if needed
    if (pagination.total_pages > 1) {
        targetsHtml += createPaginationHTML(pagination, currentPage);
    }
    
    container.innerHTML = targetsHtml;
}

/**
 * Create pagination HTML
 */
function createPaginationHTML(pagination, currentPage) {
    const totalPages = pagination.total_pages || 1;
    let paginationHtml = `
        <nav aria-label="Targets pagination" class="mt-3">
            <ul class="pagination pagination-sm justify-content-center">
    `;
    
    // Previous button
    paginationHtml += `
        <li class="page-item ${currentPage <= 1 ? 'disabled' : ''}">
            <button class="page-link" onclick="loadTargetsData(${currentPage - 1})" 
                    ${currentPage <= 1 ? 'disabled' : ''} title="Previous page">
                <i class="fas fa-chevron-left"></i>
            </button>
        </li>
    `;
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        paginationHtml += `
            <li class="page-item">
                <button class="page-link" onclick="loadTargetsData(1)">1</button>
            </li>
        `;
        if (startPage > 2) {
            paginationHtml += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHtml += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <button class="page-link" onclick="loadTargetsData(${i})">${i}</button>
            </li>
        `;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHtml += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        paginationHtml += `
            <li class="page-item">
                <button class="page-link" onclick="loadTargetsData(${totalPages})">${totalPages}</button>
            </li>
        `;
    }
    
    // Next button
    paginationHtml += `
        <li class="page-item ${currentPage >= totalPages ? 'disabled' : ''}">
            <button class="page-link" onclick="loadTargetsData(${currentPage + 1})" 
                    ${currentPage >= totalPages ? 'disabled' : ''} title="Next page">
                <i class="fas fa-chevron-right"></i>
            </button>
        </li>
    `;
    
    paginationHtml += `
            </ul>
        </nav>
    `;
    
    return paginationHtml;
}

/**
 * Sort targets
 */
function sortTargets(sortBy) {
    // Reload current page data with sort parameter
    loadTargetsData(1, 10, sortBy);
}

/**
 * Copy to clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        Utils.showToast('Copied to clipboard', 'success');
    }).catch(err => {
        console.error('Copy failed:', err);
        Utils.showToast('Copy failed', 'error');
    });
}