/**
 * 靶点模块JavaScript - 处理列表和详情页面的所有功能
 */

let targetsTable = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 根据当前页面初始化相应功能
    if (document.getElementById('targetsTable')) {
        initializeTargetsListPage();
    }
    
    if (window.targetData) {
        initializeTargetDetailPage();
    }
});

/**
 * 初始化靶点列表页面
 */
function initializeTargetsListPage() {
    initializeDataTable();
    bindListPageEvents();
    
    // 设置初始筛选值
    if (window.pageConfig) {
        // if (window.pageConfig.geneFamily && window.pageConfig.geneFamily !== 'all') {
        //     document.getElementById('familyFilter').value = window.pageConfig.geneFamily;
        // }
        if (window.pageConfig.searchQuery) {
            document.getElementById('searchInput').value = window.pageConfig.searchQuery;
        }
    }
}

/**
 * 初始化DataTables
 */
function initializeDataTable() {
    targetsTable = $('#targetsTable').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/api/targets',
            type: 'GET',
            data: function(d) {
                // 转换DataTables参数为我们的API格式
                return {
                    page: Math.floor(d.start / d.length) + 1,
                    page_size: d.length,
                    // gene_family: document.getElementById('familyFilter').value !== 'all' ? 
                    //             document.getElementById('familyFilter').value : null,
                    search: document.getElementById('searchInput').value || null,
                    sort_by: getColumnName(d.order[0].column),
                    sort_order: d.order[0].dir
                };
            },
            dataSrc: function(json) {
                // 转换我们的API响应为DataTables格式
                return json.data.items || [];
            },
            error: function(xhr, error, thrown) {
                console.error('DataTable error:', error);
                Utils.showToast('数据加载失败', 'error');
            }
        },
        columns: [
            {
                data: 'gene_name',
                title: '基因名称',
                render: function(data, type, row) {
                    return data || row.gene_symbol || '<span class="text-muted">Unknown</span>';
                }
            },
            {
                data: 'gene_symbol',
                title: '基因符号',
                width: '120px',
                render: function(data) {
                    return data ? `<code>${data}</code>` : '<span class="text-muted">N/A</span>';
                }
            },
            {
                data: 'prediction_count',
                title: '预测次数',
                width: '100px',
                render: function(data) {
                    return data ? `<span class="badge bg-primary">${data}</span>` : '0';
                }
            },
            {
                data: 'avg_score',
                title: '平均得分',
                width: '120px',
                render: function(data) {
                    if (!data) return '<span class="text-muted">N/A</span>';
                    const score = parseFloat(data);
                    const scoreClass = score >= 0.95 ? 'success' : score >= 0.90 ? 'warning' : 'secondary';
                    return `<span class="badge bg-${scoreClass}">${score.toFixed(4)}</span>`;
                }
            },
            {
                data: 'uniprot_id',
                title: 'UniProt ID',
                width: '120px',
                render: function(data) {
                    if (!data) return '<span class="text-muted">N/A</span>';
                    return `<a href="https://www.uniprot.org/uniprot/${data}" target="_blank" class="text-decoration-none">
                        ${data} <i class="fas fa-external-link-alt small"></i>
                    </a>`;
                }
            },
            {
                data: null,
                title: '操作',
                orderable: false,
                width: '100px',
                render: function(data, type, row) {
                    const geneName = row.gene_symbol || row.gene_name || 'unknown';
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" onclick="viewTarget('${geneName}')" title="查看详情">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-outline-success" onclick="viewCompounds('${geneName}')" title="相关化合物">
                                <i class="fas fa-atom"></i>
                            </button>
                        </div>
                    `;
                }
            }
        ],
        pageLength: 20,
        lengthMenu: [[10, 20, 50], [10, 20, 50]],
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/zh.json'
        },
        order: [[2, 'desc']] // 按预测次数降序排列
    });
}

/**
 * 绑定列表页面事件
 */
function bindListPageEvents() {
    // 筛选器变化
    // document.getElementById('familyFilter').addEventListener('change', function() {
    //     targetsTable.ajax.reload();
    // });
    
    // 搜索输入框回车
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            targetsTable.ajax.reload();
        }
    });
    
    // 实时搜索（防抖）
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            targetsTable.ajax.reload();
        }, 500);
    });
}

/**
 * 获取列名
 */
function getColumnName(columnIndex) {
    const columnNames = [
        'gene_name', 'gene_symbol', 'prediction_count', 'avg_score', 
        'uniprot_id', null
    ];
    return columnNames[columnIndex] || 'prediction_count';
}

/**
 * 查看靶点详情
 */
function viewTarget(geneName) {
    window.location.href = `/targets/${encodeURIComponent(geneName)}`;
}

/**
 * 查看相关化合物
 */
function viewCompounds(geneName) {
    window.location.href = `/targets/${encodeURIComponent(geneName)}#compounds`;
}

/**
 * 初始化靶点详情页面
 */
function initializeTargetDetailPage() {
    loadCompoundsData();
}

/**
 * 加载相关化合物数据
 */
async function loadCompoundsData() {
    const container = document.getElementById('compoundsContainer');
    const countBadge = document.getElementById('compoundCount');
    
    if (!container || !window.targetData) return;
    
    try {
        let compounds = [];
        
        // 如果已有数据就直接使用
        if (window.targetData.associated_compounds) {
            compounds = window.targetData.associated_compounds;
        } else {
            // 否则通过API获取
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
                加载相关化合物失败
            </div>
        `;
        countBadge.textContent = '0';
    }
}

/**
 * 显示相关化合物
 */
function displayCompounds(compounds) {
    const container = document.getElementById('compoundsContainer');
    const countBadge = document.getElementById('compoundCount');
    
    if (!compounds || compounds.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-info-circle fa-2x mb-3"></i>
                <p>暂无相关化合物数据</p>
            </div>
        `;
        countBadge.textContent = '0';
        return;
    }
    
    countBadge.textContent = compounds.length;
    
    // 按得分排序并取前20个
    const sortedCompounds = compounds.sort((a, b) => (b.score || 0) - (a.score || 0));
    const displayCompounds = sortedCompounds.slice(0, 20);
    
    // 生成化合物列表HTML
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
                            类型: ${compound.compound_type || 'N/A'}
                            ${compound.molecular_formula ? ` • 分子式: ${compound.molecular_formula}` : ''}
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
    
    // 如果有更多化合物，添加查看全部提示
    if (sortedCompounds.length > 20) {
        compoundsHtml += `
            <div class="text-center mt-3">
                <small class="text-muted">
                    显示前20个高得分化合物，共${sortedCompounds.length}个化合物
                </small>
            </div>
        `;
    }
    
    container.innerHTML = compoundsHtml;
}