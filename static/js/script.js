document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysis-form');
    const themeToggle = document.getElementById('theme-toggle');
    // 主题初始化与切换
    initTheme();
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    const resultSection = document.getElementById('result-section');
    const resultContent = document.getElementById('result-content');
    const analyzeBtn = document.getElementById('analyze-btn');
    const fillwordBtn = document.getElementById('fillword-btn');
    const fillwordSection = document.getElementById('fillword-section');
    const fillwordFrameworkSection = document.getElementById('fillword-framework-section');
    const cipaiSearch = document.getElementById('cipai-search');
    const cipaiSuggestions = document.getElementById('cipai-suggestions');
    const startFillwordBtn = document.getElementById('start-fillword-btn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const loadingSpinner = analyzeBtn.querySelector('.loading-spinner');

    // 分析表单提交事件
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        const data = {
            text: formData.get('text'),
            rhymebook: formData.get('rhymebook')
        };

        // 隐藏填词相关区域
        hideAllSections();
        
        // 显示加载状态
        setLoadingState(true);

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            if (!result.success) {
                showToast(result.error || '分析失败', 'error');
                return;
            }
            displayResult(result.data);
        } catch (error) {
            console.error('Error:', error);
            showToast('网络错误，请稍后重试', 'error');
        } finally {
            setLoadingState(false);
        }
    });

    // 填词按钮点击事件
    fillwordBtn.addEventListener('click', async function() {
        // 隐藏其他区域
        hideAllSections();
        
        // 显示填词选择区域
        fillwordSection.style.display = 'block';
        
        // 滚动到填词区域
        fillwordSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
        
        // 加载词牌列表
        await loadCipaiList();
    });

    // 词牌搜索相关变量
    let cipaiList = [];
    let selectedCipai = null;
    let currentSuggestionIndex = -1;

    // 词牌搜索输入事件
    cipaiSearch.addEventListener('input', function() {
        const query = this.value.trim();
        if (query.length === 0) {
            hideCipaiSuggestions();
            hideStartFillwordBtn();
            return;
        }
        
        const suggestions = searchCipai(query);
        showCipaiSuggestions(suggestions, query);
    });

    // 词牌搜索键盘事件
    cipaiSearch.addEventListener('keydown', function(e) {
        const suggestions = cipaiSuggestions.querySelectorAll('.cipai-suggestion-item:not(.no-suggestions)');
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentSuggestionIndex = Math.min(currentSuggestionIndex + 1, suggestions.length - 1);
            updateSuggestionSelection(suggestions);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentSuggestionIndex = Math.max(currentSuggestionIndex - 1, -1);
            updateSuggestionSelection(suggestions);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (currentSuggestionIndex >= 0 && suggestions[currentSuggestionIndex]) {
                selectCipaiSuggestion(suggestions[currentSuggestionIndex]);
            }
        } else if (e.key === 'Escape') {
            hideCipaiSuggestions();
        }
    });

    // 点击其他地方隐藏建议
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.cipai-search-container')) {
            hideCipaiSuggestions();
        }
    });

    // 开始填词按钮点击事件
    startFillwordBtn.addEventListener('click', async function() {
        if (!selectedCipai) {
            alert('请先选择词牌');
            return;
        }
        
        await loadFillwordFramework(selectedCipai.cipai_name, selectedCipai.author);
    });

    // 隐藏所有结果区域
    function hideAllSections() {
        resultSection.style.display = 'none';
        fillwordSection.style.display = 'none';
        fillwordFrameworkSection.style.display = 'none';
    }

    // 设置加载状态
    function setLoadingState(isLoading) {
        if (isLoading) {
            analyzeBtn.disabled = true;
            btnText.style.display = 'none';
            loadingSpinner.style.display = 'block';
        } else {
            analyzeBtn.disabled = false;
            btnText.style.display = 'block';
            loadingSpinner.style.display = 'none';
        }
    }

    // 加载词牌列表
    async function loadCipaiList() {
        try {
            const response = await fetch('/get_cipai_list');
            const result = await response.json();
            
            if (result.success) {
                // 保存词牌列表到全局变量
                cipaiList = result.data.cipai_list;
                
                // 设置默认选项（竹枝+皇甫松+14）
                if (result.data.default_index >= 0 && result.data.default_index < result.data.cipai_list.length) {
                    const defaultCipai = result.data.cipai_list[result.data.default_index];
                    selectCipai(defaultCipai);
                    cipaiSearch.value = defaultCipai.cipai_name;
                }
            } else {
                console.error('获取词牌列表失败:', result.error);
                showToast('获取词牌列表失败：' + (result.error || ''), 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('网络错误，请稍后重试', 'error');
        }
    }

    // 搜索词牌
    function searchCipai(query) {
        if (!cipaiList || cipaiList.length === 0) {
            return [];
        }
        
        const lowerQuery = query.toLowerCase();
        return cipaiList.filter(cipai => {
            return cipai.cipai_name.toLowerCase().includes(lowerQuery) ||
                   cipai.author.toLowerCase().includes(lowerQuery) ||
                   cipai.cipai_name.includes(query) ||
                   cipai.author.includes(query);
        }).slice(0, 10); // 限制显示前10个结果
    }

    // 显示词牌建议
    function showCipaiSuggestions(suggestions, query) {
        currentSuggestionIndex = -1;
        
        if (suggestions.length === 0) {
            cipaiSuggestions.innerHTML = '<div class="no-suggestions">未找到匹配的词牌</div>';
        } else {
            cipaiSuggestions.innerHTML = suggestions.map(cipai => {
                const nameHighlighted = highlightMatch(cipai.cipai_name, query);
                const authorHighlighted = highlightMatch(cipai.author, query);
                
                return `
                    <div class="cipai-suggestion-item" data-cipai-name="${cipai.cipai_name}" data-author="${cipai.author}">
                        <div class="cipai-suggestion-name">${nameHighlighted}</div>
                        <div class="cipai-suggestion-info">${authorHighlighted} - ${cipai.total_chars}字</div>
                    </div>
                `;
            }).join('');
            
            // 添加点击事件
            cipaiSuggestions.querySelectorAll('.cipai-suggestion-item').forEach(item => {
                item.addEventListener('click', function() {
                    selectCipaiSuggestion(this);
                });
            });
        }
        
        cipaiSuggestions.style.display = 'block';
    }

    // 隐藏词牌建议
    function hideCipaiSuggestions() {
        cipaiSuggestions.style.display = 'none';
        currentSuggestionIndex = -1;
    }

    // 更新建议选择状态
    function updateSuggestionSelection(suggestions) {
        suggestions.forEach((item, index) => {
            if (index === currentSuggestionIndex) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }

    // 选择词牌建议
    function selectCipaiSuggestion(suggestionElement) {
        const cipaiName = suggestionElement.dataset.cipaiName;
        const author = suggestionElement.dataset.author;
        
        // 找到对应的词牌对象
        const cipai = cipaiList.find(c => c.cipai_name === cipaiName && c.author === author);
        if (cipai) {
            selectCipai(cipai);
            cipaiSearch.value = cipaiName;
            hideCipaiSuggestions();
        }
    }

    // 选择词牌
    function selectCipai(cipai) {
        selectedCipai = cipai;
        showStartFillwordBtn();
    }

    // 高亮匹配文本
    function highlightMatch(text, query) {
        if (!query) return text;
        
        const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi');
        return text.replace(regex, '<span class="cipai-suggestion-highlight">$1</span>');
    }

    // 转义正则表达式特殊字符
    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // 显示开始填词按钮
    function showStartFillwordBtn() {
        startFillwordBtn.style.display = 'block';
    }

    // 隐藏开始填词按钮
    function hideStartFillwordBtn() {
        startFillwordBtn.style.display = 'none';
        selectedCipai = null;
    }

    // 加载填词框架
    async function loadFillwordFramework(cipaiName, author) {
        try {
            const response = await fetch('/get_fillword_framework', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cipai_name: cipaiName,
                    author: author
                })
            });

            const result = await response.json();
            
            if (result.success) {
                displayFillwordFramework(result.data);
            } else {
                console.error('获取填词框架失败:', result.error);
                showToast('获取填词框架失败：' + (result.error || ''), 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('网络错误，请稍后重试', 'error');
        }
    }

    // 显示填词框架
    function displayFillwordFramework(result) {
        const frameworkContent = document.getElementById('fillword-framework-content');
        
        let html = `
            <div class="result-item compact">
                <div class="result-label">词牌信息：</div>
                <div class="result-value">${result.cipai_name} - ${result.author} (${result.total_chars}字)</div>
            </div>
        `;
        
        html += '<div class="fillword-framework">';
        
        // 为每一阕创建输入框架
        result.framework.ques.forEach((que, queIndex) => {
            // 为上阕（第一个阕）添加粘贴按钮
            const pasteButton = queIndex === 0 ? 
                '<button type="button" class="paste-btn" onclick="pasteFromClipboard()" title="从剪贴板粘贴">📋</button>' : '';
            
            html += `
                <div class="fillword-que">
                    <div class="fillword-que-title-container">
                        <div class="fillword-que-title">${que.name} (${que.length}字)</div>
                        ${pasteButton}
                    </div>
            `;
            
            // 为整个阕创建一行，每句用逗号分隔
            html += '<div class="fillword-que-line">';
            
            que.sentences.forEach((sentence, sentenceIndex) => {
                // 如果不是第一句，添加逗号分隔符
                if (sentenceIndex > 0) {
                    html += '<span class="fillword-comma">，</span>';
                }
                
                // 添加句子容器
                html += '<span class="fillword-sentence-inline">';
                
                sentence.forEach((tone, toneIndex) => {
                    const globalIndex = getGlobalToneIndex(result.framework.ques, queIndex, sentenceIndex, toneIndex);
                    
                    html += `
                        <input type="text" 
                               class="fillword-char-input fillword-char-input-inline" 
                               data-tone="${tone}"
                               data-global-index="${globalIndex}"
                               maxlength="1"
                               placeholder="${tone}">
                    `;
                });
                
                html += '</span>'; // 结束句子
            });
            
            html += '</div>'; // 结束阕行
            

            
            html += '</div>'; // 结束阕
        });
        
        html += '</div>'; // 结束框架
        
        // 添加图例容器（紧贴下阕外部）
        html += `
            <div class="fillword-legend-container">
                <div class="fillword-legend" id="fillword-legend">
                    <div class="fillword-legend-items">
                        <div class="fillword-legend-item">
                            <input type="text" class="fillword-legend-demo" value="" readonly>
                            <span class="fillword-legend-text">中</span>
                        </div>
                        <div class="fillword-legend-item">
                            <input type="text" class="fillword-legend-demo tone-correct" value="" readonly>
                            <span class="fillword-legend-text">正确</span>
                        </div>
                        <div class="fillword-legend-item">
                            <input type="text" class="fillword-legend-demo tone-error" value="" readonly>
                            <span class="fillword-legend-text">错误</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 添加操作按钮
        html += `
            <div class="fillword-actions">
                <button type="button" class="fillword-action-btn fillword-clear-btn" onclick="clearFillwordFramework()">
                    清空
                </button>
                <button type="button" class="fillword-action-btn fillword-check-btn" onclick="checkFillwordText()">
                    检查平仄
                </button>
                <button type="button" class="fillword-action-btn fillword-final-btn" id="final-analysis-btn" onclick="finalAnalysis()" disabled>
                    最终分析
                </button>
            </div>
        `;
        
        frameworkContent.innerHTML = html;
        
        // 显示填词框架区域
        fillwordFrameworkSection.style.display = 'block';
        
        // 添加输入框事件监听器
        addFillwordInputListeners();
        
        // 初始化最终分析按钮状态
        updateFinalAnalysisButtonState();
        
        // 滚动到填词框架区域
        fillwordFrameworkSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }

    // 获取全局音调索引
    function getGlobalToneIndex(ques, queIndex, sentenceIndex, toneIndex) {
        let globalIndex = 0;
        
        // 累加前面所有阕的字数
        for (let i = 0; i < queIndex; i++) {
            globalIndex += ques[i].length;
        }
        
        // 累加当前阕前面所有句子的字数
        for (let i = 0; i < sentenceIndex; i++) {
            globalIndex += ques[queIndex].sentences[i].length;
        }
        
        // 加上当前句子中的位置
        globalIndex += toneIndex;
        
        return globalIndex;
    }



    // 添加填词输入框事件监听器
    function addFillwordInputListeners() {
        const inputs = document.querySelectorAll('.fillword-char-input');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                // 限制只能输入汉字
                this.value = this.value.replace(/[^\u4e00-\u9fa5]/g, '');
                
                // 自动跳转到下一个输入框
                if (this.value.length === 1) {
                    const nextInput = getNextFillwordInput(this);
                    if (nextInput) {
                        nextInput.focus();
                    }
                }
                
                // 每次输入后检查是否所有字都填好，更新最终分析按钮状态
                updateFinalAnalysisButtonState();
            });
            
            input.addEventListener('keydown', function(e) {
                // 支持退格键跳转到上一个输入框
                if (e.key === 'Backspace' && this.value === '') {
                    const prevInput = getPreviousFillwordInput(this);
                    if (prevInput) {
                        prevInput.focus();
                    }
                }
                
                // 支持空格键跳转到下一个输入框
                if (e.key === ' ' || e.key === 'Spacebar') {
                    e.preventDefault(); // 阻止空格输入
                    const nextInput = getNextFillwordInput(this);
                    if (nextInput) {
                        nextInput.focus();
                    }
                }
            });
            
            // 监听删除字符（退格键和删除键）来更新最终分析按钮状态
            input.addEventListener('keyup', function(e) {
                if (e.key === 'Backspace' || e.key === 'Delete') {
                    updateFinalAnalysisButtonState();
                }
            });
        });
    }

    // 获取下一个填词输入框
    function getNextFillwordInput(currentInput) {
        const allInputs = Array.from(document.querySelectorAll('.fillword-char-input'));
        const currentIndex = allInputs.indexOf(currentInput);
        
        if (currentIndex !== -1 && currentIndex < allInputs.length - 1) {
            return allInputs[currentIndex + 1];
        }
        
        return null;
    }

    // 获取上一个填词输入框
    function getPreviousFillwordInput(currentInput) {
        const allInputs = Array.from(document.querySelectorAll('.fillword-char-input'));
        const currentIndex = allInputs.indexOf(currentInput);
        
        if (currentIndex > 0) {
            return allInputs[currentIndex - 1];
        }
        
        return null;
    }

    function displayResult(result) {
        let html = '';

        // 基本信息（全宽显示）
        html += `
            <div class="result-item full-width">
                <div class="result-label">输入文本：</div>
                <div class="result-value">${result.original_text || result.text}</div>
            </div>
        `;

        // 开始网格布局容器 - 用于短信息项（词牌名、作者、平仄得分）
        html += '<div class="result-grid">';

        // 词牌名
        if (result.cipai_name) {
            html += `
                <div class="result-item compact">
                    <div class="result-label">识别词牌：</div>
                    <div class="result-value">${result.cipai_name}</div>
                </div>
            `;

            if (result.author) {
                html += `
                    <div class="result-item compact">
                        <div class="result-label">参考作者：</div>
                        <div class="result-value">${result.author}</div>
                    </div>
                `;
            }
        }

        // 平仄得分
        if (result.score !== undefined) {
            const scoreClass = getScoreClass(result.score);
            html += `
                <div class="result-item compact">
                    <div class="result-label">平仄得分：</div>
                    <div class="result-value">
                        <span class="${scoreClass}">${result.score}%</span>
                    </div>
                </div>
            `;
        }

        // 结束网格布局容器
        html += '</div>';

        // 文本统计（单独一行，因为内容较长）
        html += `
            <div class="result-item compact">
                <div class="result-label">文本统计：</div>
                <div class="result-value">
                    总字数：${result.length} 字，分段字数：[${result.split_length.join(', ')}]
                </div>
            </div>
        `;

        // 词牌介绍（如果有的话，全宽显示）
        if (result.cipai_name && result.cipai_intro && result.cipai_intro.trim() !== '') {
            html += `
                <div class="result-item full-width">
                    <div class="result-label">词牌介绍：</div>
                    <div class="result-value cipai-intro">${result.cipai_intro}</div>
                </div>
            `;
        }

        // 平仄标注（全宽显示）
        if (result.tone_text && result.tone_text.length > 0) {
            html += `
                <div class="result-item full-width">
                    <div class="result-label">平仄标注：</div>
                    <div class="tone-display">
                        ${createToneDisplay(result.tone_text, result.issues || [])}
                    </div>
                </div>
            `;
        }

        // 平仄合规提示
        if (result.score === 100) {
            html += `
                <div class="result-item full-width">
                    <div class="success-message">🎉 恭喜！全部平仄合规！</div>
                </div>
            `;
        }

        // 韵脚标注显示
        if (result.yunjiao_detailed && result.yunjiao_detailed.length > 0) {
            // 韵脚选择器HTML（如果有多个模式）
            let yunjiaoSelectorHtml = '';
            if (result.yunjiao_options && result.yunjiao_options.length > 1) {
                yunjiaoSelectorHtml = `
                    <select id="yunjiao-selector" class="yunjiao-selector-inline">
                        ${result.yunjiao_options.map((option, index) => 
                            `<option value="${option.id}" ${index === 0 ? 'selected' : ''}>
                                模式 ${option.id + 1}：${option.positions.length}个韵脚 (${option.words.slice(0, 5).join('、')}${option.words.length > 5 ? '...' : ''})
                            </option>`
                        ).join('')}
                    </select>
                `;
            }
            
            html += `
                <div class="result-item full-width">
                    <div class="result-label">
                        韵脚标注：${yunjiaoSelectorHtml}
                    </div>
                    <div class="yunjiao-annotated-text" id="yunjiao-annotated-text">
                        ${createAnnotatedText(result.text, result.yunjiao_detailed)}
                    </div>
                </div>
            `;

            // 韵脚统计（使用网格布局）
            html += `
                <div class="result-item full-width">
                    <div class="result-label">韵脚统计：</div>
                    <div class="yunjiao-summary" id="yunjiao-summary">
                        ${result.yunjiao_detailed.map(item => 
                            `<div class="yunjiao-summary-item">
                                <span class="yunjiao-char">${item.word}</span>
                                <span class="yunjiao-yunbu">
                                    ${item.yunbu.length > 0 ? item.yunbu.join('、') : '未找到韵部'}
                                </span>
                            </div>`
                        ).join('')}
                    </div>
                </div>
            `;
        }

        resultContent.innerHTML = html;
        resultSection.style.display = 'block';
        
        // 添加韵脚模式选择器事件监听器
        const yunjiaoSelector = document.getElementById('yunjiao-selector');
        if (yunjiaoSelector && result.yunjiao_options) {
            yunjiaoSelector.addEventListener('change', function() {
                handleYunjiaoSelection(this.value, result);
            });
        }
        
        // 滚动到结果区域
        resultSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }

    function displayError(message) {
        showToast(message || '发生错误', 'error');
    }

    function getScoreClass(score) {
        if (score >= 90) return 'score-high';
        if (score >= 70) return 'score-medium';
        return 'score-low';
    }

    function getToneClass(tone) {
        switch (tone) {
            case '平': return 'tone-ping';
            case '仄': return 'tone-ze';
            default: return 'tone-unknown';
        }
    }

    // 创建带有不合平仄字突出显示的平仄标注
    function createToneDisplay(toneText, issues) {
        // 创建不合平仄字的位置集合，使用后端提供的精确位置信息
        const issuePositions = new Set();
        const issueDetailMap = {};
        
        // 使用后端提供的位置信息精确标记错误字符
        issues.forEach(issue => {
            if (issue.position !== undefined) {
                issuePositions.add(issue.position);
                issueDetailMap[issue.position] = issue;
            }
        });

        return toneText.map(([char, tone], index) => {
            if (issuePositions.has(index)) {
                // 这是一个不合平仄的字
                const issue = issueDetailMap[index];
                const basicToneClass = getToneClass(tone);
                const tooltipText = `错误：实际为"${issue.actual}"，应为"${issue.expected}"`;
                return `<span class="tone-char ${basicToneClass} tone-incorrect" title="错误：${issue.actual}→${issue.expected}">
                    ${char}
                    <span class="tone-incorrect-tooltip">${tooltipText}</span>
                </span>`;
            } else {
                // 正常的字
                const toneClass = getToneClass(tone);
                return `<span class="tone-char ${toneClass}" title="${tone}">${char}</span>`;
            }
        }).join('');
    }

    // 创建带韵脚标注的文本
    function createAnnotatedText(text, yunjiaoDetailed) {
        if (!text || !yunjiaoDetailed || yunjiaoDetailed.length === 0) {
            // 如果没有韵脚信息，按阕分行显示
            return formatTextByQue(text);
        }

        // 创建位置到韵脚信息的映射
        const positionMap = {};
        yunjiaoDetailed.forEach(item => {
            positionMap[item.position] = item;
        });

        // 找到阕的分隔位置
        const queBreakPositions = findQueBreakPositions(text);

        let result = '';
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            
            if (positionMap[i]) {
                // 这是一个韵脚字
                const yunjiaoInfo = positionMap[i];
                const yunbuText = yunjiaoInfo.yunbu.length > 0 
                    ? yunjiaoInfo.yunbu.join('、') 
                    : '未知韵部';
                
                result += `<span class="yunjiao-char-annotated" title="韵脚字：${char}，韵部：${yunbuText}">
                    ${char}
                    <span class="yunjiao-tooltip">${yunbuText}</span>
                </span>`;
            } else {
                result += char;
            }
            
            // 在阕分隔位置添加换行
            if (queBreakPositions.includes(i)) {
                result += '<br/><br/>'; // 阕间用两个换行分隔，更清晰
            }
        }
        return result;
    }

    // 根据阕结构格式化文本显示
    function formatTextByQue(text) {
        const breakPoint = findQueBreakPoint(text);
        
        if (breakPoint > 0 && breakPoint < text.length - 1) {
            const shangque = text.substring(0, breakPoint + 1);
            const xiaque = text.substring(breakPoint + 1);
            return shangque + '<br/><br/>' + xiaque;
        }
        
        // 如果无法找到合适的分隔点，返回原文
        return text;
    }

    // 找到阕的分隔位置
    function findQueBreakPositions(text) {
        const breakPoint = findQueBreakPoint(text);
        return breakPoint > 0 && breakPoint < text.length - 1 ? [breakPoint] : [];
    }

    // 智能寻找阕的分隔点
    function findQueBreakPoint(text) {
        const textLength = text.length;
        const centerPoint = Math.floor(textLength / 2);
        
        // 定义搜索范围：中心点前后30%的范围
        const searchRange = Math.floor(textLength * 0.3);
        const searchStart = Math.max(Math.floor(textLength * 0.3), centerPoint - searchRange);
        const searchEnd = Math.min(Math.floor(textLength * 0.7), centerPoint + searchRange);
        
        // 收集搜索范围内的标点符号位置
        const punctuationPositions = [];
        
        for (let i = searchStart; i <= searchEnd; i++) {
            const char = text[i];
            if (char === '。') {
                // 句号的优先级最高
                punctuationPositions.push({ pos: i, priority: 3, char: char });
            } else if (char === '，') {
                // 逗号的优先级中等
                punctuationPositions.push({ pos: i, priority: 2, char: char });
            } else if (char === '、' || char === '；') {
                // 顿号和分号的优先级较低
                punctuationPositions.push({ pos: i, priority: 1, char: char });
            }
        }
        
        if (punctuationPositions.length === 0) {
            // 如果搜索范围内没有标点，返回中心点
            return centerPoint;
        }
        
        // 按优先级和距离中心点的远近排序
        punctuationPositions.sort((a, b) => {
            // 首先按优先级排序（高优先级在前）
            if (a.priority !== b.priority) {
                return b.priority - a.priority;
            }
            // 同等优先级下，距离中心点越近越好
            const distanceA = Math.abs(a.pos - centerPoint);
            const distanceB = Math.abs(b.pos - centerPoint);
            return distanceA - distanceB;
        });
        
        // 返回最佳分隔点
        return punctuationPositions[0].pos;
    }

    // 处理韵脚模式选择
    async function handleYunjiaoSelection(selectedId, originalResult) {
        const formData = new FormData(form);
        const data = {
            text: formData.get('text'),
            rhymebook: formData.get('rhymebook'),
            cipai_name: originalResult.cipai_name,
            author: originalResult.author,
            yunjiao_id: parseInt(selectedId)
        };

        try {
            const response = await fetch('/select_yunjiao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (result.success) {
                // 更新韵脚标注显示
                const yunjiaoAnnotatedText = document.getElementById('yunjiao-annotated-text');
                const yunjiaoSummary = document.getElementById('yunjiao-summary');
                
                if (yunjiaoAnnotatedText) {
                    yunjiaoAnnotatedText.innerHTML = createAnnotatedText(originalResult.text, result.data.yunjiao_detailed);
                }
                
                if (yunjiaoSummary) {
                    yunjiaoSummary.innerHTML = result.data.yunjiao_detailed.map(item => 
                        `<div class="yunjiao-summary-item">
                            <span class="yunjiao-char">${item.word}</span>
                            <span class="yunjiao-yunbu">
                                ${item.yunbu.length > 0 ? item.yunbu.join('、') : '未找到韵部'}
                            </span>
                        </div>`
                    ).join('');
                }
            } else {
                console.error('韵脚模式选择错误:', result.error);
                showToast('韵脚模式选择失败：' + (result.error || ''), 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('网络错误，请稍后重试', 'error');
        }
    }

    // 添加示例文本按钮功能
    const textInput = document.getElementById('text-input');
    
    // 示例诗词（双击输入框自动填入）
    const examples = [
        `梅梅柳柳斗纤秾。乱山中。为谁容。试著春衫，依旧怯东风。何处踏青人未去，呼女伴，认骄骢。儿家门户几重重。记相逢。画桥东。明日重来，风雨暗残红。可惜行云春不管，裙带褪，鬓云松。`,
        `落日古城角，把酒劝君留。长安路远，何事风雪敝貂裘。散尽黄金身世，不管秦楼人怨，归计狎沙鸥。明夜扁舟去，和月载离愁。功名事，身未老，几时休。诗书万卷，致身须到古伊周。莫学班超投笔，纵得封侯万里，憔悴老边州。何处依刘客，寂寞赋登楼。`,
        `池上主人，人适忘鱼，鱼适还忘水。洋洋乎，翠藻青萍里。想鱼兮、无便于此。尝试思，庄周正谈两事。一明豕虱一羊蚁。说蚁慕于膻，于蚁弃知，又说于羊弃意。甚虱焚于豕独忘之。却骤说于鱼为得计。千古遗文，我不知言，以我非子。子固非鱼，噫。鱼之为计子焉知。河水深且广，风涛万顷堪依。有网罟如云，鹈鹕成阵，过而留泣计应非。其外海茫茫，下有龙伯，饥时一啖千里。更任公五十犗为饵。使海上人人厌腥味。似鹍鹏、变化能几。东游入海，此计直以命为嬉。古来谬算狂图，五鼎烹死，指为平地。嗟鱼欲事远游时。请三思而行可矣。`
    ];

    // 双击输入框填入示例
    textInput.addEventListener('dblclick', function() {
        if (!this.value.trim()) {
            const randomExample = examples[Math.floor(Math.random() * examples.length)];
            this.value = randomExample;
            this.focus();
        }
    });

    // 检查是否所有填词输入框都已填好
    function updateFinalAnalysisButtonState() {
        const finalBtn = document.getElementById('final-analysis-btn');
        if (!finalBtn) return;
        
        const inputs = document.querySelectorAll('.fillword-char-input');
        let allFilled = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                allFilled = false;
            }
        });
        
        finalBtn.disabled = !allFilled;
    }
    
    // 最终分析功能
    function finalAnalysis() {
        const inputs = document.querySelectorAll('.fillword-char-input');
        
        if (inputs.length === 0) {
            alert('未找到填词输入框');
            return;
        }
        
        // 构建带标点的文本
        let text = buildFormattedText(inputs);
        
        if (!text.trim()) {
            alert('请先填写词内容');
            return;
        }
        
        // 将填写的文本放入分析输入框
        const textInput = document.getElementById('text-input');
        textInput.value = text;
        
        // 隐藏填词相关区域
        hideAllSections();
        
        // 显示输入区域
        const inputSection = document.querySelector('.input-section');
        if (inputSection) {
            inputSection.style.display = 'block';
        }
        
        // 滚动到顶部
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // 延迟一下再触发分析，确保界面更新完成
        setTimeout(() => {
            // 模拟点击分析按钮
            const analyzeBtn = document.getElementById('analyze-btn');
            if (analyzeBtn) {
                analyzeBtn.click();
            }
        }, 300);
    }

    // 构建带标点符号的格式化文本
    function buildFormattedText(inputs) {
        // 根据填词框架的结构来组织文本
        const fillwordFramework = document.querySelector('.fillword-framework');
        if (!fillwordFramework) {
            // 如果没有找到框架结构，则简单连接所有字符
            return Array.from(inputs).map(input => input.value.trim()).join('');
        }
        
        let text = '';
        
        // 遍历所有的阕
        const ques = fillwordFramework.querySelectorAll('.fillword-que');
        
        ques.forEach((que, queIndex) => {
            // 获取这一阕中的所有句子容器
            const sentences = que.querySelectorAll('.fillword-sentence-inline');
            
            sentences.forEach((sentence, sentenceIndex) => {
                // 获取这个句子中的所有输入框
                const sentenceInputs = sentence.querySelectorAll('.fillword-char-input');
                
                // 添加这个句子的所有字符
                sentenceInputs.forEach(input => {
                    if (input.value.trim()) {
                        text += input.value.trim();
                    }
                });
                
                // 在句子之间添加逗号（除了阕内最后一句）
                if (sentenceIndex < sentences.length - 1) {
                    text += '，';
                }
            });
            
            // 阕间标点逻辑：上下阕之间加句号
            if (queIndex < ques.length - 1) {
                text += '。';
            }
        });
        
        // 在最后一阕结束后也加句号
        if (text && !text.endsWith('。')) {
            text += '。';
        }
        
        return text;
    }

    // 将函数暴露到全局作用域，供HTML中的onclick使用
    window.clearFillwordFramework = clearFillwordFramework;
    window.checkFillwordText = checkFillwordToneInline;
    window.finalAnalysis = finalAnalysis;
    window.updateFinalAnalysisButtonState = updateFinalAnalysisButtonState;
    window.pasteFromClipboard = pasteFromClipboard;
    window.showFillwordLegend = showFillwordLegend;
    window.hideFillwordLegend = hideFillwordLegend;
});
// 初始化主题（从 localStorage 或系统偏好）
function initTheme() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const useDark = saved ? saved === 'dark' : prefersDark;
    document.body.classList.toggle('dark', useDark);
    updateThemeToggleText(useDark);
}

// 切换主题并持久化
function toggleTheme() {
    const isDark = document.body.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeToggleText(isDark);
}

function updateThemeToggleText(isDark) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    // 仅使用图标，无文字
    btn.textContent = isDark ? '☀️' : '🌙';
}

// 清空填词框架
function clearFillwordFramework() {
    const inputs = document.querySelectorAll('.fillword-char-input');
    inputs.forEach(input => {
        input.value = '';
        // 清除平仄检查的样式
        input.classList.remove('tone-error', 'tone-correct');
    });

    // 聚焦到第一个输入框
    if (inputs.length > 0) {
        inputs[0].focus();
    }
    // 更新最终分析按钮状态
    updateFinalAnalysisButtonState();
}

// 统一Toast组件
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `paste-notification paste-notification-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 页面内平仄检查函数
async function checkFillwordToneInline() {
    const inputs = document.querySelectorAll('.fillword-char-input');
    
    // 清除之前的错误标记
    inputs.forEach(input => {
        input.classList.remove('tone-error', 'tone-correct');
    });
    
    // 移除未使用的空值检查，避免无意义的变量
    
    // 直接检查平仄，不需要弹窗确认
    
    // 静默进行平仄检查
    
    try {
        // 检查每个字符的平仄
        for (const input of inputs) {
            const char = input.value.trim();
            const expectedTone = input.getAttribute('data-tone');
            
            if (char && expectedTone && expectedTone !== '中') {
                const actualTone = await getCharacterTone(char);
                
                if (actualTone === expectedTone) {
                    input.classList.add('tone-correct');
                } else {
                    input.classList.add('tone-error');
                }
            }
        }
        
        // 检查完成，结果已通过颜色在页面上显示
    } catch (error) {
        console.error('平仄检查错误:', error);
    }
}

// 获取汉字的平仄（使用API调用）
async function getCharacterTone(char) {
    try {
        // 调用后端API获取汉字平仄（统一返回结构）
        const response = await fetch('/get_char_tone', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ char: char })
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result && result.success && result.data && result.data.tone) {
                return result.data.tone;
            }
        }
    } catch (error) {
        console.log('获取平仄信息失败，使用简化判断:', error);
    }
    
    // 如果API调用失败，使用简化的平仄判断
    return getCharacterToneSimple(char);
}

// 简化的平仄判断（备用方案）
function getCharacterToneSimple(char) {
    // 常见平声字（一声、二声）
    const pingTones = '东冬江支微鱼虞齐佳灰真文元寒删先萧宵肴豪歌麻阳唐庚青蒸尤侵覃盐咸山仙';
    
    // 常见仄声字（三声、四声）
    const zeTones = '董肿讲纸尾语麌荠蟹贿轸吻阮旱潸铣筱巧皓马养荡梗迥有寝感俭验产愿绛迎';
    
    if (pingTones.includes(char)) {
        return '平';
    } else if (zeTones.includes(char)) {
        return '仄';
    } else {
        // 根据Unicode编码的简单判断
        const unicode = char.charCodeAt(0);
        return (unicode % 2 === 0) ? '平' : '仄';
    }
}

// 从剪贴板粘贴功能
async function pasteFromClipboard() {
    try {
        // 检查是否支持剪贴板API
        if (!navigator.clipboard || !navigator.clipboard.readText) {
            alert('您的浏览器不支持剪贴板访问功能，请手动复制粘贴。');
            return;
        }

        // 读取剪贴板内容
        const text = await navigator.clipboard.readText();
        
        if (!text || text.trim().length === 0) {
            alert('剪贴板内容为空，请先复制要粘贴的文本。');
            return;
        }

        // 去除所有标点符号，只保留汉字
        const cleanText = text.replace(/[^\u4e00-\u9fa5]/g, '');
        
        if (cleanText.length === 0) {
            alert('剪贴板中没有找到汉字内容。');
            return;
        }

        // 获取所有填词输入框
        const inputs = document.querySelectorAll('.fillword-char-input');
        
        if (inputs.length === 0) {
            alert('请先选择词牌并进入填词界面。');
            return;
        }

        // 检查字数是否匹配
        if (cleanText.length > inputs.length) {
            const result = confirm(`剪贴板内容有 ${cleanText.length} 个字，但当前词牌只有 ${inputs.length} 个位置。\n\n是否只粘贴前 ${inputs.length} 个字？`);
            if (!result) {
                return;
            }
        } else if (cleanText.length < inputs.length) {
            const result = confirm(`剪贴板内容只有 ${cleanText.length} 个字，但当前词牌有 ${inputs.length} 个位置。\n\n是否继续粘贴（剩余位置保持空白）？`);
            if (!result) {
                return;
            }
        }

        // 清空所有输入框
        inputs.forEach(input => {
            input.value = '';
        });

        // 逐字填入输入框
        const maxLength = Math.min(cleanText.length, inputs.length);
        for (let i = 0; i < maxLength; i++) {
            inputs[i].value = cleanText[i];
            
            // 添加短暂延迟以产生逐字填入的视觉效果
            if (i < maxLength - 1) {
                await new Promise(resolve => setTimeout(resolve, 50));
            }
        }

        // 更新最终分析按钮状态
        updateFinalAnalysisButtonState();
        
        // 聚焦到第一个空白输入框或最后一个填入的输入框
        const nextEmptyInput = Array.from(inputs).find(input => !input.value.trim());
        if (nextEmptyInput) {
            nextEmptyInput.focus();
        } else if (maxLength < inputs.length) {
            inputs[maxLength].focus();
        } else {
            inputs[inputs.length - 1].focus();
        }

        // 显示成功提示
        const successMsg = `成功粘贴 ${maxLength} 个字！`;
        showPasteNotification(successMsg, 'success');

    } catch (error) {
        console.error('粘贴失败:', error);
        
        if (error.name === 'NotAllowedError') {
            alert('浏览器拒绝了剪贴板访问权限。\n\n请在浏览器设置中允许此网站访问剪贴板，或手动复制粘贴。');
        } else {
            alert('粘贴操作失败，请重试或手动输入。\n\n错误信息：' + error.message);
        }
    }
}

// 显示填词图例
function showFillwordLegend() {
    const legend = document.getElementById('fillword-legend');
    if (legend) {
        legend.style.display = 'block';
        // 添加淡入动画效果
        legend.style.opacity = '0';
        legend.style.transition = 'opacity 0.3s ease-in-out';
        setTimeout(() => {
            legend.style.opacity = '1';
        }, 10);
    }
}

// 隐藏填词图例
function hideFillwordLegend() {
    const legend = document.getElementById('fillword-legend');
    if (legend) {
        legend.style.display = 'none';
    }
}

// 显示粘贴通知
function showPasteNotification(message, type = 'success') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `paste-notification paste-notification-${type}`;
    notification.textContent = message;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 显示动画
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // 3秒后自动隐藏
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
} 