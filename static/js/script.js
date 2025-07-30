document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysis-form');
    const resultSection = document.getElementById('result-section');
    const resultContent = document.getElementById('result-content');
    const analyzeBtn = document.getElementById('analyze-btn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const loadingSpinner = analyzeBtn.querySelector('.loading-spinner');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        const data = {
            text: formData.get('text'),
            rhymebook: formData.get('rhymebook'),
            cipai: formData.get('cipai')
        };

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
            displayResult(result);
        } catch (error) {
            console.error('Error:', error);
            displayError('网络错误，请稍后重试');
        } finally {
            setLoadingState(false);
        }
    });

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

    function displayResult(result) {
        if (result.error) {
            displayError(result.error);
            return;
        }

        if (!result.success) {
            displayError(result.message || '分析失败');
            return;
        }

        let html = '';

        // 基本信息
        html += `
            <div class="result-item">
                <div class="result-label">输入文本：</div>
                <div class="result-value">${result.text}</div>
            </div>
        `;

        // 词牌名
        if (result.cipai_name) {
            html += `
                <div class="result-item">
                    <div class="result-label">识别词牌：</div>
                    <div class="result-value">${result.cipai_name}</div>
                </div>
            `;

            if (result.author) {
                html += `
                    <div class="result-item">
                        <div class="result-label">参考作者：</div>
                        <div class="result-value">${result.author}</div>
                    </div>
                `;
            }
        }

        // 文本统计
        html += `
            <div class="result-item">
                <div class="result-label">文本统计：</div>
                <div class="result-value">
                    总字数：${result.length} 字，分段字数：[${result.split_length.join(', ')}]
                </div>
            </div>
        `;

        // 平仄得分
        if (result.score !== undefined) {
            const scoreClass = getScoreClass(result.score);
            html += `
                <div class="result-item">
                    <div class="result-label">平仄得分：</div>
                    <div class="result-value">
                        <span class="${scoreClass}">${result.score}%</span>
                    </div>
                </div>
            `;
        }

        // 平仄标注
        if (result.tone_text && result.tone_text.length > 0) {
            html += `
                <div class="result-item">
                    <div class="result-label">平仄标注：</div>
                    <div class="tone-display">
                        ${result.tone_text.map(([char, tone]) => {
                            const toneClass = getToneClass(tone);
                            return `<span class="tone-char ${toneClass}" title="${tone}">${char}</span>`;
                        }).join('')}
                    </div>
                </div>
            `;
        }

        // 不合平仄的字
        if (result.issues && result.issues.length > 0) {
            html += `
                <div class="result-item">
                    <div class="result-label">不合平仄的字：</div>
                    <ul class="issues-list">
                        ${result.issues.map(issue => 
                            `<li class="issue-item">
                                字："${issue.word}" - 实际：${issue.actual}，应为：${issue.expected}
                            </li>`
                        ).join('')}
                    </ul>
                </div>
            `;
        } else if (result.score === 100) {
            html += `
                <div class="result-item">
                    <div class="success-message">🎉 恭喜！全部平仄合规！</div>
                </div>
            `;
        }

        // 韵脚字
        if (result.yunjiao_words && result.yunjiao_words.length > 0) {
            html += `
                <div class="result-item">
                    <div class="result-label">韵脚字：</div>
                    <div class="yunjiao-list">
                        ${result.yunjiao_words.map(word => 
                            `<span class="yunjiao-item">${word}</span>`
                        ).join('')}
                    </div>
                </div>
            `;

            // 韵脚韵部
            if (result.yunjiao_yunbu) {
                html += `
                    <div class="result-item">
                        <div class="result-label">韵脚韵部：</div>
                        <div class="result-value">
                            ${Object.entries(result.yunjiao_yunbu).map(([word, yunbu]) => 
                                `<div>${word}：${yunbu.length > 0 ? yunbu.join('、') : '未找到韵部'}</div>`
                            ).join('')}
                        </div>
                    </div>
                `;
            }
        }

        resultContent.innerHTML = html;
        resultSection.style.display = 'block';
        
        // 滚动到结果区域
        resultSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }

    function displayError(message) {
        resultContent.innerHTML = `
            <div class="error-message">
                ❌ ${message}
            </div>
        `;
        resultSection.style.display = 'block';
        
        // 滚动到结果区域
        resultSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
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

    // 添加示例文本按钮功能
    const textInput = document.getElementById('text-input');
    
    // 可以添加一些示例诗词
    const examples = [
        "梅梅柳柳斗纤秾。乱山中。为谁容。试著春衫，依旧怯东风。何处踏青人未去，呼女伴，认骄骢。儿家门户几重重。记相逢。画桥东。明日重来，风雨暗残红。可惜行云春不管，裙带褪，鬓云松。",
        "寻寻觅觅，冷冷清清，凄凄惨惨戚戚。乍暖还寒时候，最难将息。三杯两盏淡酒，怎敌他、晚来风急？雁过也，正伤心，却是旧时相识。",
        "昨夜雨疏风骤，浓睡不消残酒。试问卷帘人，却道海棠依旧。知否，知否？应是绿肥红瘦。"
    ];

    // 双击输入框填入示例
    textInput.addEventListener('dblclick', function() {
        if (!this.value.trim()) {
            const randomExample = examples[Math.floor(Math.random() * examples.length)];
            this.value = randomExample;
            this.focus();
        }
    });
}); 