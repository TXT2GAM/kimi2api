// 全局变量
let currentPage = 1;
let perPage = 15;
let deleteTokenId = null;
let envVarsCount = 0;

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    setupNavigation();
    loadTokens();
    loadEnvVars();
});

// 导航设置
function setupNavigation() {
    const navLinks = document.querySelectorAll('#nav-tabs .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tab = this.getAttribute('data-tab');
            switchTab(tab);
            
            // 更新活动状态
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// 切换标签页
function switchTab(tab) {
    const pages = document.querySelectorAll('.tab-content');
    pages.forEach(page => page.style.display = 'none');
    
    if (tab === 'tokens') {
        document.getElementById('tokens-page').style.display = 'block';
        loadTokens();
    } else if (tab === 'env') {
        document.getElementById('env-page').style.display = 'block';
        loadEnvVars();
    }
}

// Token 管理功能
async function addTokens() {
    const tokenInput = document.getElementById('token-input');
    const tokens = (tokenInput.value || '').trim().split('\n').filter(t => t.trim());
    
    if (tokens.length === 0) {
        showAlert('请输入至少一个 Token', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/tokens/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ tokens: tokens })
        });

        const result = await response.json();
        
        if (response.ok) {
            showAlert(`成功添加 ${result.tokens.length} 个 Token`, 'success');
            tokenInput.value = '';
            loadTokens();
        } else {
            showAlert('添加失败: ' + result.detail, 'danger');
        }
    } catch (error) {
        showAlert('网络错误: ' + error.message, 'danger');
    }
}

async function loadTokens() {
    try {
        const response = await fetch(`/api/tokens?page=${currentPage}&per_page=${perPage}`);
        const data = await response.json();
        
        if (response.ok) {
            renderTokenTable(data.tokens);
            renderPagination(data.page, data.total_pages, data.total);
        } else {
            showAlert('加载 Token 失败', 'danger');
        }
    } catch (error) {
        showAlert('网络错误: ' + error.message, 'danger');
    }
}

function renderTokenTable(tokens) {
    const tbody = document.getElementById('token-table-body');
    tbody.innerHTML = '';
    
    tokens.forEach((token, index) => {
        const row = document.createElement('tr');
        row.className = token.is_expired ? 'token-expired' : 'token-valid';
        
        const displayToken = token.token.length > 50 ? 
            token.token.substring(0, 20) + '...' + token.token.substring(token.token.length - 20) : 
            token.token;
        
        row.innerHTML = `
            <td>${(currentPage - 1) * perPage + index + 1}</td>
            <td>
                <code class="small">${displayToken}</code>
                <button class="btn btn-sm btn-outline-secondary ms-1" onclick="copyToClipboard('${token.token}')" title="复制完整Token">
                    <i class="bi bi-clipboard"></i>
                </button>
            </td>
            <td>${token.exp_time_beijing}</td>
            <td>
                ${token.is_expired ? 
                    '<span class="badge bg-danger">即将过期</span>' : 
                    '<span class="badge bg-success">有效</span>'
                }
            </td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteToken(${token.id})">
                    <i class="bi bi-trash"></i> 删除
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function renderPagination(page, totalPages, total) {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';
    
    if (totalPages <= 1) return;
    
    // 上一页
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${page === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" onclick="changePage(${page - 1})">上一页</a>`;
    pagination.appendChild(prevLi);
    
    // 页码
    const startPage = Math.max(1, page - 2);
    const endPage = Math.min(totalPages, page + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === page ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#" onclick="changePage(${i})">${i}</a>`;
        pagination.appendChild(li);
    }
    
    // 下一页
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${page === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" onclick="changePage(${page + 1})">下一页</a>`;
    pagination.appendChild(nextLi);
    
    // 总数显示
    const infoLi = document.createElement('li');
    infoLi.className = 'page-item disabled';
    infoLi.innerHTML = `<span class="page-link">共 ${total} 条</span>`;
    pagination.appendChild(infoLi);
}

function changePage(page) {
    currentPage = page;
    loadTokens();
}

function changePerPage() {
    perPage = parseInt(document.getElementById('per-page-select').value);
    currentPage = 1;
    loadTokens();
}

function deleteToken(tokenId) {
    deleteTokenId = tokenId;
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

async function confirmDelete() {
    if (!deleteTokenId) return;
    
    try {
        const response = await fetch(`/api/tokens/${deleteTokenId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('Token 删除成功', 'success');
            loadTokens();
        } else {
            showAlert('删除失败', 'danger');
        }
    } catch (error) {
        showAlert('网络错误: ' + error.message, 'danger');
    }
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
    modal.hide();
    deleteTokenId = null;
}


// 环境变量管理功能
async function loadEnvVars() {
    try {
        const response = await fetch('/api/env');
        const envVars = await response.json();
        
        if (response.ok) {
            renderEnvVars(envVars);
        } else {
            showAlert('加载环境变量失败', 'danger');
        }
    } catch (error) {
        showAlert('网络错误: ' + error.message, 'danger');
    }
}

function renderEnvVars(envVars) {
    const container = document.getElementById('env-vars-container');
    container.innerHTML = '';
    envVarsCount = 0;
    
    // 只显示固定的环境变量
    const fixedVars = [
        'AUTH_KEY',
        'MAX_CONNECTIONS', 
        'MAX_KEEPALIVE_CONNECTIONS',
        'KEEPALIVE_EXPIRY',
        'HOST',
        'PORT'
    ];
    
    fixedVars.forEach(key => {
        const value = envVars[key] || '';
        addFixedEnvVarRow(key, value);
    });
}

// 移除添加环境变量功能，因为只允许固定变量

function addFixedEnvVarRow(key, value = '') {
    const container = document.getElementById('env-vars-container');
    const row = document.createElement('div');
    row.className = 'row mb-3';
    row.id = `env-row-${envVarsCount}`;
    
    // 获取变量描述
    const descriptions = {
        'AUTH_KEY': '鉴权密钥',
        'MAX_CONNECTIONS': '最大连接数',
        'MAX_KEEPALIVE_CONNECTIONS': '最大保持活动连接数', 
        'KEEPALIVE_EXPIRY': '连接保持时间(秒)',
        'HOST': '服务器地址',
        'PORT': '服务器端口'
    };
    
    const description = descriptions[key] || key;
    
    row.innerHTML = `
        <div class="col-md-3">
            <label class="form-label">${description}</label>
            <input type="text" class="form-control" value="${key}" readonly>
        </div>
        <div class="col-md-9">
            <label class="form-label">配置值</label>
            <input type="text" class="form-control" placeholder="请填入${description}" value="${value}" id="env-value-${envVarsCount}" data-key="${key}">
        </div>
    `;
    
    container.appendChild(row);
    envVarsCount++;
}

// 移除删除环境变量功能，因为只允许固定变量

async function saveEnvVars() {
    const envVars = {};
    
    // 收集所有环境变量值
    const container = document.getElementById('env-vars-container');
    const valueInputs = container.querySelectorAll('input[data-key]');
    
    valueInputs.forEach(input => {
        const key = input.getAttribute('data-key');
        const value = input.value.trim();
        if (key && value) {
            envVars[key] = value;
        }
    });
    
    try {
        const response = await fetch('/api/env', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(envVars)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert('环境变量保存成功 (需重启服务生效)', 'success');
        } else {
            showAlert('保存失败: ' + result.detail, 'danger');
        }
    } catch (error) {
        showAlert('网络错误: ' + error.message, 'danger');
    }
}

async function applyEnvVarsLive() {
    const envVars = {};
    
    // 收集所有环境变量值
    const container = document.getElementById('env-vars-container');
    const valueInputs = container.querySelectorAll('input[data-key]');
    
    valueInputs.forEach(input => {
        const key = input.getAttribute('data-key');
        const value = input.value.trim();
        if (key && value) {
            envVars[key] = value;
        }
    });
    
    if (Object.keys(envVars).length === 0) {
        showAlert('请先填写配置值', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/env/apply', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(envVars)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(`配置已实时应用！更新了 ${Object.keys(result.updated || {}).length} 项配置`, 'success');
            
            // 显示更新的配置详情
            if (result.updated && Object.keys(result.updated).length > 0) {
                const details = Object.entries(result.updated)
                    .map(([key, value]) => `${key}: ${value}`)
                    .join(', ');
                setTimeout(() => {
                    showAlert(`更新详情: ${details}`, 'info', 5000);
                }, 1000);
            }
        } else {
            showAlert('实时应用失败: ' + (result.detail || '未知错误'), 'danger');
        }
    } catch (error) {
        showAlert('网络错误: ' + error.message, 'danger');
    }
}

// 工具函数
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Token 已复制到剪贴板', 'success', 2000);
    }).catch(() => {
        showAlert('复制失败', 'danger');
    });
}

function showAlert(message, type, duration = 3000) {
    // 创建警告框
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
    `;
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // 自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, duration);
}