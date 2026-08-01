/**
 * Nocturne AI — 对话交互逻辑
 * 处理消息发送、SSE 流式接收、Markdown 渲染
 */
(function () {
    'use strict';

    const messagesList = document.getElementById('messages-list');
    const messagesContainer = document.getElementById('messages-container');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatForm = document.getElementById('chat-form');
    const charCount = document.getElementById('char-count');
    const toggleSidebarBtn = document.getElementById('toggle-sidebar');
    const sidebar = document.getElementById('sidebar');
    const conversationTitle = document.getElementById('conversation-title');
    const emptyState = document.getElementById('empty-state');

    let currentConversationId = window.__CURRENT_CONVERSATION_ID__ || null;
    let isStreaming = false;

    // ==================== 初始化 ====================

    function init() {
        renderInitialMessages();
        bindEvents();
        // 初始化图标
        if (window.lucide) lucide.createIcons();
    }

    function renderInitialMessages() {
        const messages = window.__INITIAL_MESSAGES__ || [];
        if (messages.length === 0) return;
        if (emptyState) emptyState.style.display = 'none';
        messages.forEach(msg => appendMessage(msg.role, msg.content, false));
        scrollToBottom();
    }

    // ==================== 事件绑定 ====================

    function bindEvents() {
        // 输入框自动高度与字数统计
        messageInput.addEventListener('input', () => {
            autoResize(messageInput);
            const len = messageInput.value.length;
            charCount.textContent = len;
            sendButton.disabled = len === 0 || isStreaming;
        });

        // Enter 发送，Shift+Enter 换行
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!sendButton.disabled) chatForm.requestSubmit();
            }
        });

        // 表单提交
        chatForm.addEventListener('submit', handleSubmit);

        // 侧边栏折叠
        if (toggleSidebarBtn) {
            toggleSidebarBtn.addEventListener('click', () => {
                if (window.innerWidth >= 768) {
                    // 桌面端：折叠/展开
                    sidebar.classList.toggle('sidebar-collapsed');
                } else {
                    // 手机端：打开/关闭抽屉
                    sidebar.classList.toggle('-translate-x-full');
                    const overlay = document.getElementById('sidebar-overlay');
                    if (overlay) overlay.classList.toggle('hidden');
                }
            });
        }

        // 点击遮罩层关闭侧边栏（手机端）
        const overlay = document.getElementById('sidebar-overlay');
        if (overlay) {
            overlay.addEventListener('click', () => {
                sidebar.classList.add('-translate-x-full');
                overlay.classList.add('hidden');
            });
        }

        // 建议卡片点击
        document.querySelectorAll('.suggestion-card').forEach(card => {
            card.addEventListener('click', () => {
                const text = card.querySelector('p').textContent;
                messageInput.value = text;
                messageInput.dispatchEvent(new Event('input'));
                messageInput.focus();
            });
        });
    }

    function autoResize(el) {
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 160) + 'px';
    }

    // ==================== 发送消息 ====================

    async function handleSubmit(e) {
        e.preventDefault();
        const text = messageInput.value.trim();
        if (!text || isStreaming) return;

        // 隐藏空状态
        if (emptyState) emptyState.style.display = 'none';

        // 渲染用户消息
        appendMessage('user', text);
        scrollToBottom();

        // 清空输入框
        messageInput.value = '';
        autoResize(messageInput);
        charCount.textContent = '0';
        sendButton.disabled = true;
        isStreaming = true;

        // 创建 AI 思考占位
        const aiEl = appendMessage('assistant', '', true);
        const contentEl = aiEl.querySelector('.message-content');
        renderThinking(contentEl);

        try {
            await streamChat(text, contentEl);
        } catch (err) {
            contentEl.innerHTML = '<span class="text-red-400">连接失败，请重试</span>';
            console.error(err);
        } finally {
            isStreaming = false;
            sendButton.disabled = messageInput.value.length === 0;
        }
    }

    // ==================== SSE 流式接收 ====================

    async function streamChat(message, contentEl) {
        const response = await fetch('/chat/api/chat/stream/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                conversation_id: currentConversationId,
            }),
        });

        if (!response.ok) throw new Error('请求失败: ' + response.status);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // 保留不完整的行

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = line.slice(6).trim();
                if (!data) continue;

                try {
                    const event = JSON.parse(data);
                    if (event.type === 'start') {
                        // 更新当前会话 ID
                        if (event.conversation_id && !currentConversationId) {
                            currentConversationId = event.conversation_id;
                            // 更新 URL 不刷新页面
                            history.replaceState(null, '', `/chat/${event.conversation_id}/`);
                        }
                        // 清除思考动画，准备接收
                        contentEl.innerHTML = '';
                    } else if (event.type === 'token') {
                        fullText += event.content;
                        contentEl.innerHTML = renderMarkdown(fullText) + '<span class="typing-cursor"></span>';
                        scrollToBottom();
                    } else if (event.type === 'done') {
                        currentConversationId = event.conversation_id;
                        contentEl.innerHTML = renderMarkdown(fullText);
                        scrollToBottom();
                        // 刷新侧边栏标题
                        if (conversationTitle && fullText) {
                            conversationTitle.textContent = message.slice(0, 20) + (message.length > 20 ? '…' : '');
                        }
                    }
                } catch (e) {
                    // 忽略解析错误
                }
            }
        }
    }

    // ==================== 消息渲染 ====================

    function appendMessage(role, content, isEmpty = false) {
        const wrapper = document.createElement('div');
        wrapper.className = 'flex gap-3 animate-slide-in ' + (role === 'user' ? 'justify-end' : '');

        if (role === 'user') {
            wrapper.innerHTML = `
                <div class="max-w-[80%] px-5 py-3 rounded-2xl rounded-br-sm border border-nocturne-mint/30 bg-nocturne-mint/5 text-sm">
                    <div class="message-content">${escapeHtml(content)}</div>
                </div>
            `;
        } else {
            wrapper.innerHTML = `
                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-nocturne-mint/40 to-nocturne-amber/20 flex items-center justify-center mt-1">
                    <div class="w-2.5 h-2.5 rounded-full bg-nocturne-mint shadow-[0_0_8px_rgba(94,234,212,0.8)]"></div>
                </div>
                <div class="max-w-[85%] px-5 py-3 rounded-2xl rounded-tl-sm bg-nocturne-elevated/60 border border-nocturne-border">
                    <div class="message-content text-sm">${isEmpty ? '' : renderMarkdown(content)}</div>
                </div>
            `;
        }

        messagesList.appendChild(wrapper);
        if (window.lucide) lucide.createIcons();
        return wrapper;
    }

    function renderThinking(el) {
        el.innerHTML = `
            <div class="thinking-dots">
                <span></span><span></span><span></span>
            </div>
        `;
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // ==================== 轻量 Markdown 渲染 ====================

    function renderMarkdown(text) {
        if (!text) return '';
        let html = escapeHtml(text);

        // 代码块 ```lang\ncode\n```
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
            return `<pre><code>${code.trim()}</code></pre>`;
        });

        // 行内代码 `code`
        html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');

        // 粗体 **text**
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // 列表 - item
        html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);

        // 换行
        html = html.replace(/\n/g, '<br>');

        // 清理 ul 内多余的 br
        html = html.replace(/<ul>(<br>)*/g, '<ul>');
        html = html.replace(/(<br>)*<\/ul>/g, '</ul>');

        return html;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ==================== 启动 ====================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
