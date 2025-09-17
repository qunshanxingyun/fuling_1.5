/**
 * 首页专用JavaScript
 */

// 从HTML中获取数据
function getStatsData() {
    const statsElement = document.getElementById('stats-data');
    if (statsElement) {
        try {
            return JSON.parse(statsElement.textContent);
        } catch (e) {
            console.error('Failed to parse stats data:', e);
            return { compounds: { by_type: {} }, targets: { gene_families: {} } };
        }
    }
    return { compounds: { by_type: {} }, targets: { gene_families: {} } };
}

// 搜索功能
function searchCompounds() {
    const query = document.getElementById('compoundSearch').value.trim();
    if (query) {
        window.location.href = `/compounds/search?q=${encodeURIComponent(query)}`;
    } else {
        window.location.href = `/compounds`;
    }
}

function searchTargets() {
    const query = document.getElementById('targetSearch').value.trim();
    if (query) {
        window.location.href = `/targets/search?q=${encodeURIComponent(query)}`;
    } else {
        window.location.href = `/targets`;
    }
}

// 回车搜索事件
function bindSearchEvents() {
    const compoundSearch = document.getElementById('compoundSearch');
    const targetSearch = document.getElementById('targetSearch');
    
    if (compoundSearch) {
        compoundSearch.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchCompounds();
            }
        });
    }
    
    if (targetSearch) {
        targetSearch.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchTargets();
            }
        });
    }
}

// 初始化图表
// function initializeCharts() {
//     const stats = getStatsData();
    
//     // 化合物分布图
//     initializeCompoundChart(stats.compounds.by_type);
    
//     // 靶点家族分布图
//     initializeTargetChart(stats.targets.gene_families);
// }

function initializeCompoundChart(compoundData) {
    const ctx = document.getElementById('compoundChart');
    if (!ctx || !compoundData || Object.keys(compoundData).length === 0) {
        console.warn('Compound chart data not available');
        return;
    }
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(compoundData),
            datasets: [{
                data: Object.values(compoundData),
                backgroundColor: [
                    '#FF6384',
                    '#36A2EB', 
                    '#FFCE56',
                    '#4BC0C0'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function initializeTargetChart(targetData) {
    const ctx = document.getElementById('targetChart');
    if (!ctx || !targetData || Object.keys(targetData).length === 0) {
        console.warn('Target chart data not available');
        return;
    }
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(targetData),
            datasets: [{
                label: '靶点数量',
                data: Object.values(targetData),
                backgroundColor: [
                    '#28a745',
                    '#17a2b8',
                    '#ffc107'
                ],
                borderColor: [
                    '#1e7e34',
                    '#138496', 
                    '#e0a800'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return `${context[0].label}家族`;
                        },
                        label: function(context) {
                            return `靶点数量: ${context.parsed.y}`;
                        }
                    }
                }
            }
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 绑定搜索事件
    bindSearchEvents();
    
    // 初始化图表（延迟执行确保Chart.js已加载）
    setTimeout(initializeCharts, 100);
});

// 导出函数供全局使用
window.searchCompounds = searchCompounds;
window.searchTargets = searchTargets;