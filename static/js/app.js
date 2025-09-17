/**
 * 茯苓靶点预测数据库 - 主应用脚本
 * 包含通用功能和搜索页面功能
 */

// 全局变量
window.APP = {
    API_BASE: '/api',
    VERSION: '2.0'
};

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    
    // 如果是搜索页面，初始化搜索功能
    if (document.getElementById('globalSearchInput')) {
        initializeSearchPage();
    }
});

/**
 * 初始化应用
 */
function initializeApp() {
    // 初始化工具提示
    initializeTooltips();
    
    // 初始化数据表格
    initializeDataTables();
    
    // 设置AJAX默认配置
    setupAjaxDefaults();
    
    // 绑定全局事件
    bindGlobalEvents();
}

/**
 * 初始化搜索页面
 */
function initializeSearchPage() {
    bindSearchEvents();
    
    // 如果有初始查询，自动执行搜索
    if (window.pageConfig && window.pageConfig.initialQuery) {
        document.getElementById('globalSearchInput').value = window.pageConfig.initialQuery;
        performGlobalSearch();
    }
}

/**
 * 绑定搜索页面事件
 */
function bindSearchEvents() {
    // 搜索按钮点击
    document.getElementById('searchBtn').addEventListener('click', performGlobalSearch);
    
    // 回车搜索
    document.getElementById('globalSearchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performGlobalSearch();
        }
    });
    
    // 搜索建议点击
    document.querySelectorAll('.search-example').forEach(example => {
        example.addEventListener('click', function() {
            const query = this.getAttribute('data-query');
            const scope = this.getAttribute('data-scope');
            
            document.getElementById('globalSearchInput').value = query;
            document.getElementById(`scope${scope.charAt(0).toUpperCase() + scope.slice(1)}`).checked = true;
            
            performGlobalSearch();
        });
    });
}

/**
 * 执行全局搜索
 */
async function performGlobalSearch() {
    const query = document.getElementById('globalSearchInput').value.trim();
    const scope = document.querySelector('input[name="searchScope"]:checked').value;
    
    if (!query) {
        Utils.showToast('请输入搜索关键词', 'warning');
        return;
    }
    
    showSearchLoading();
    
    try {
        let compoundsResults = [];
        let targetsResults = [];
        
        // 根据搜索范围执行搜索
        if (scope === 'all' || scope === 'compounds') {
            const compoundsResponse = await apiClient.post('/compounds/search', {
                query: query,
                type: 'all'
            });
            compoundsResults = compoundsResponse.data || [];
        }
        
        if (scope === 'all' || scope === 'targets') {
            const targetsResponse = await apiClient.post('/targets/search', {
                query: query,
                type: 'all'
            });
            targetsResults = targetsResponse.data || [];
        }
        
        displaySearchResults(compoundsResults, targetsResults, query);
        
    } catch (error) {
        console.error('Search error:', error);
        showNoResults();
        Utils.showToast('搜索失败：' + error.message, 'error');
    }
}

/**
 * 显示搜索加载状态
 */
function showSearchLoading() {
    document.getElementById('searchResults').style.display = 'none';
    document.getElementById('noResults').style.display = 'none';
    document.getElementById('searchSuggestions').style.display = 'none';
    document.getElementById('loadingResults').style.display = 'block';
}

/**
 * 显示搜索结果
 */
function displaySearchResults(compounds, targets, query) {
    const totalCount = compounds.length + targets.length;
    
    if (totalCount === 0) {
        showNoResults();
        return;
    }
    
    // 隐藏其他状态
    document.getElementById('loadingResults').style.display = 'none';
    document.getElementById('noResults').style.display = 'none';
    document.getElementById('searchSuggestions').style.display = 'none';
    
    // 显示结果容器
    document.getElementById('searchResults').style.display = 'block';
    
    // 更新统计信息
    document.getElementById('totalCount').textContent = totalCount;
    document.getElementById('compoundsCount').textContent = compounds.length;
    document.getElementById('targetsCount').textContent = targets.length;
    
    // 显示化合物结果
    if (compounds.length > 0) {
        document.getElementById('compoundsResults').style.display = 'block';
        document.getElementById('compoundsBadge').textContent = compounds.length;
        displayCompoundsResults(compounds);
    } else {
        document.getElementById('compoundsResults').style.display = 'none';
    }
    
    // 显示靶点结果
    if (targets.length > 0) {
        document.getElementById('targetsResults').style.display = 'block';
        document.getElementById('targetsBadge').textContent = targets.length;
        displayTargetsResults(targets);
    } else {
        document.getElementById('targetsResults').style.display = 'none';
    }
}

/**
 * 显示化合物结果
 */
function displayCompoundsResults(compounds) {
    const container = document.getElementById('compoundsContainer');
    
    const html = compounds.slice(0, 10).map(compound => `
        <div class="border-bottom pb-3 mb-3">
            <div class="row">
                <div class="col-md-8">
                    <h6 class="mb-1">
                        <a href="/compounds/${compound.global_id}" class="text-decoration-none">
                            ${compound.chinese_name || compound.Name || '未命名'}
                        </a>
                    </h6>
                    ${compound.Name !== compound.chinese_name && compound.Name ? 
                        `<p class="text-muted small mb-1">${compound.Name}</p>` : ''}
                    <div class="small text-muted">
                        ID: ${compound.global_id} • 类型: 
                        <span class="badge bg-${compound.compound_type === '挥发油' ? 'success' : 
                                                compound.compound_type === '三萜' ? 'info' : 'warning'} badge-sm">
                            ${compound.compound_type}
                        </span>
                        ${compound.Molecular_Formula ? ` • 分子式: <code>${compound.Molecular_Formula}</code>` : ''}
                    </div>
                </div>
                <div class="col-md-4 text-end">
                    <div class="btn-group btn-group-sm">
                        <a href="/compounds/${compound.global_id}" class="btn btn-outline-primary">
                            <i class="fas fa-eye"></i> 详情
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    if (compounds.length > 10) {
        container.innerHTML = html + `
            <div class="text-center">
                <a href="/compounds?search=${encodeURIComponent(document.getElementById('globalSearchInput').value)}" 
                   class="btn btn-outline-success">
                    查看全部 ${compounds.length} 个化合物结果
                </a>
            </div>
        `;
    } else {
        container.innerHTML = html;
    }
}

/**
 * 显示靶点结果
 */
function displayTargetsResults(targets) {
    const container = document.getElementById('targetsContainer');
    
    const html = targets.slice(0, 10).map(target => `
        <div class="border-bottom pb-3 mb-3">
            <div class="row">
                <div class="col-md-8">
                    <h6 class="mb-1">
                        <a href="/targets/${encodeURIComponent(target.gene_symbol || target.gene_name)}" 
                           class="text-decoration-none">
                            ${target.gene_name || target.gene_symbol || '未知靶点'}
                        </a>
                    </h6>
                    <div class="small text-muted">
                        ${target.gene_symbol ? `基因符号: <code>${target.gene_symbol}</code>` : ''}
                        ${target.prediction_count ? ` • 预测次数: <span class="badge bg-primary badge-sm">${target.prediction_count}</span>` : ''}
                        ${target.avg_score ? ` • 平均得分: <span class="badge bg-success badge-sm">${target.avg_score.toFixed(4)}</span>` : ''}
                    </div>
                </div>
                <div class="col-md-4 text-end">
                    <div class="btn-group btn-group-sm">
                        <a href="/targets/${encodeURIComponent(target.gene_symbol || target.gene_name)}" 
                           class="btn btn-outline-primary">
                            <i class="fas fa-eye"></i> 详情
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    if (targets.length > 10) {
        container.innerHTML = html + `
            <div class="text-center">
                <a href="/targets?search=${encodeURIComponent(document.getElementById('globalSearchInput').value)}" 
                   class="btn btn-outline-info">
                    查看全部 ${targets.length} 个靶点结果
                </a>
            </div>
        `;
    } else {
        container.innerHTML = html;
    }
}

/**
 * 显示无结果
 */
function showNoResults() {
    document.getElementById('loadingResults').style.display = 'none';
    document.getElementById('searchResults').style.display = 'none';
    document.getElementById('searchSuggestions').style.display = 'none';
    document.getElementById('noResults').style.display = 'block';
}

/**
 * 初始化Bootstrap工具提示
 */
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * 初始化DataTables
 */
function initializeDataTables() {
    // 为所有带有data-table类的表格初始化DataTables
    $('.data-table').each(function() {
        const $table = $(this);
        const options = {
            responsive: true,
            pageLength: 20,
            language: {
                url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/zh.json'
            },
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                 '<"row"<"col-sm-12"tr>>' +
                 '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            ...($table.data('table-options') || {})
        };
        
        $table.DataTable(options);
    });
}

/**
 * 设置AJAX默认配置
 */
function setupAjaxDefaults() {
    // 设置CSRF token（如果需要）
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                const token = $('meta[name=csrf-token]').attr('content');
                if (token) {
                    xhr.setRequestHeader("X-CSRFToken", token);
                }
            }
        }
    });
}

/**
 * 绑定全局事件
 */
function bindGlobalEvents() {
    // 返回顶部按钮
    $(window).scroll(function() {
        if ($(this).scrollTop() > 100) {
            $('#backToTop').fadeIn();
        } else {
            $('#backToTop').fadeOut();
        }
    });
    
    // 点击返回顶部
    $(document).on('click', '#backToTop', function() {
        $('html, body').animate({scrollTop: 0}, 600);
        return false;
    });
}

/**
 * API调用工具类
 */
class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || `HTTP Error: ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }
    
    async get(endpoint, params = {}) {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${endpoint}?${query}` : endpoint;
        return this.request(url);
    }
    
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
}

// 创建全局API客户端实例
window.apiClient = new APIClient();

/**
 * 通用工具函数
 */
const Utils = {
    /**
     * 显示加载状态
     */
    showLoading(element) {
        const $el = $(element);
        $el.html('<div class="text-center"><div class="loading-spinner"></div> 加载中...</div>');
    },
    
    /**
     * 显示错误信息
     */
    showError(element, message) {
        const $el = $(element);
        $el.html(`<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>${message}</div>`);
    },
    
    /**
     * 显示成功信息
     */
    showSuccess(element, message) {
        const $el = $(element);
        $el.html(`<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>${message}</div>`);
    },
    
    /**
     * 格式化数字
     */
    formatNumber(num, decimals = 2) {
        if (num === null || num === undefined) return 'N/A';
        return Number(num).toFixed(decimals);
    },
    
    /**
     * 格式化分子量
     */
    formatMolecularWeight(weight) {
        if (!weight) return 'N/A';
        return `${this.formatNumber(weight, 1)} g/mol`;
    },
    
    /**
     * 格式化预测得分
     */
    formatScore(score) {
        if (!score) return 'N/A';
        const formattedScore = this.formatNumber(score, 4);
        let badgeClass = 'secondary';
        
        if (score >= 0.95) badgeClass = 'success';
        else if (score >= 0.90) badgeClass = 'warning';
        else if (score >= 0.80) badgeClass = 'info';
        
        return `<span class="badge bg-${badgeClass}">${formattedScore}</span>`;
    },
    
    /**
     * 截断长文本
     */
    truncateText(text, maxLength = 50) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },
    
    /**
     * 复制到剪贴板
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('已复制到剪贴板', 'success');
        } catch (err) {
            console.error('复制失败:', err);
            this.showToast('复制失败', 'error');
        }
    },
    
    /**
     * 显示Toast通知
     */
    showToast(message, type = 'info') {
        // 创建toast元素
        const toastId = 'toast_' + Date.now();
        const toastClass = type === 'error' ? 'bg-danger' : 
                          type === 'success' ? 'bg-success' : 'bg-info';
        
        const toastHTML = `
            <div class="toast ${toastClass} text-white" id="${toastId}" role="alert">
                <div class="toast-body">
                    <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : 
                                      type === 'success' ? 'check' : 'info-circle'} me-2"></i>
                    ${message}
                </div>
            </div>
        `;
        
        // 添加到页面
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1055';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        
        // 显示toast
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 3000
        });
        toast.show();
        
        // 自动移除
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    },
    
    /**
     * 防抖函数
     */
    debounce(func, wait) {
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
};

// 将工具函数绑定到全局
window.Utils = Utils;

/**
 * 分子可视化工具
 */
class MoleculeViewer {
    constructor(containerId) {
        this.containerId = containerId;
        this.viewer = null;
    }
    
    /**
     * 从SMILES创建3D分子视图
     */
    async loadFromSMILES(smiles) {
        try {
            if (!window.$3Dmol) {
                throw new Error('3Dmol.js library not loaded');
            }
            
            // 清理现有viewer
            if (this.viewer) {
                this.viewer.clear();
            }
            
            // 创建新viewer
            const element = document.getElementById(this.containerId);
            this.viewer = $3Dmol.createViewer(element, {
                defaultcolors: $3Dmol.rasmolElementColors
            });
            
            // 这里需要调用化学信息学服务将SMILES转换为3D坐标
            // 简化示例：显示基本信息
            element.innerHTML = `
                <div class="text-center p-4">
                    <i class="fas fa-atom fa-3x text-primary mb-3"></i>
                    <p class="mb-2"><strong>SMILES:</strong></p>
                    <code class="small">${smiles}</code>
                    <p class="text-muted mt-3">3D结构可视化需要额外的化学信息学服务</p>
                </div>
            `;
            
        } catch (error) {
            console.error('Molecule visualization error:', error);
            document.getElementById(this.containerId).innerHTML = 
                '<div class="alert alert-warning">分子可视化暂时不可用</div>';
        }
    }
}

// 将分子查看器绑定到全局
window.MoleculeViewer = MoleculeViewer;

/**
 * 返回顶部按钮HTML（自动添加到body）
 */
document.addEventListener('DOMContentLoaded', function() {
    const backToTopHTML = `
        <button id="backToTop" class="btn btn-primary position-fixed" 
                style="bottom: 20px; right: 20px; z-index: 1000; display: none; border-radius: 50%; width: 50px; height: 50px;">
            <i class="fas fa-arrow-up"></i>
        </button>
    `;
    document.body.insertAdjacentHTML('beforeend', backToTopHTML);
});