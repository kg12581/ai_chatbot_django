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
    const uploadButton = document.getElementById('upload-button');
    const fileInput = document.getElementById('file-input');
    const attachmentsPreview = document.getElementById('attachments-preview');

    let currentConversationId = window.__CURRENT_CONVERSATION_ID__ || null;
    let isStreaming = false;
    // 附件队列：[{id, name, type, size, content, url, status}]
    let attachments = [];
    let attachmentIdSeq = 0;

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
            updateSendButton();
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

        // 上传按钮：触发文件选择
        if (uploadButton) {
            uploadButton.addEventListener('click', () => {
                if (isStreaming) return;
                fileInput.click();
            });
        }

        // 文件选择
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files || []);
                files.forEach(handleFileUpload);
                fileInput.value = ''; // 允许重复选择同一文件
            });
        }

        // 拖拽上传
        const formWrapper = chatForm.querySelector('.relative.flex');
        if (formWrapper) {
            ['dragover', 'dragenter'].forEach(ev => {
                formWrapper.addEventListener(ev, (e) => {
                    e.preventDefault();
                    formWrapper.classList.add('border-nocturne-mint/60');
                });
            });
            ['dragleave', 'drop'].forEach(ev => {
                formWrapper.addEventListener(ev, (e) => {
                    e.preventDefault();
                    formWrapper.classList.remove('border-nocturne-mint/60');
                });
            });
            formWrapper.addEventListener('drop', (e) => {
                e.preventDefault();
                if (isStreaming) return;
                const files = Array.from(e.dataTransfer.files || []);
                files.forEach(handleFileUpload);
            });
        }

        // 粘贴图片
        messageInput.addEventListener('paste', (e) => {
            const items = e.clipboardData?.items || [];
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    const file = item.getAsFile();
                    if (file) {
                        e.preventDefault();
                        handleFileUpload(file);
                    }
                }
            }
        });

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
        // 等待上传中的附件完成
        const pendingUploads = attachments.filter(a => a.status === 'uploading');
        if (isStreaming || pendingUploads.length > 0) return;
        // 没有文本且没有附件，不发送
        const readyAttachments = attachments.filter(a => a.status === 'done');
        if (!text && readyAttachments.length === 0) return;

        // 隐藏空状态
        if (emptyState) emptyState.style.display = 'none';

        // 渲染用户消息（含附件预览）
        appendMessage('user', text, false, readyAttachments);
        scrollToBottom();

        // 收集要发送的附件（精简字段，避免传输 url 等本地信息）
        const sendAttachments = readyAttachments.map(a => ({
            name: a.name,
            type: a.type,
            size: a.size,
            content: a.content || '',
        }));

        // 清空输入框与附件
        messageInput.value = '';
        autoResize(messageInput);
        charCount.textContent = '0';
        attachments = [];
        renderAttachmentsPreview();
        updateSendButton();
        isStreaming = true;

        // 创建 AI 思考占位
        const aiEl = appendMessage('assistant', '', true);
        const contentEl = aiEl.querySelector('.message-content');
        renderThinking(contentEl);

        try {
            await streamChat(text, contentEl, sendAttachments);
        } catch (err) {
            contentEl.innerHTML = '<span class="text-red-400">连接失败，请重试</span>';
            console.error(err);
        } finally {
            isStreaming = false;
            updateSendButton();
        }
    }

    // ==================== SSE 流式接收 ====================

    async function streamChat(message, contentEl, sendAttachments) {
        const response = await fetch('/chat/api/chat/stream/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                conversation_id: currentConversationId,
                attachments: sendAttachments || [],
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
                            const titleBase = message || (sendAttachments && sendAttachments[0] ? sendAttachments[0].name : '');
                            if (titleBase) {
                                conversationTitle.textContent = titleBase.slice(0, 20) + (titleBase.length > 20 ? '…' : '');
                            }
                        }
                    }
                } catch (e) {
                    // 忽略解析错误
                }
            }
        }
    }

    // ==================== 消息渲染 ====================

    function appendMessage(role, content, isEmpty = false, attachments = []) {
        const wrapper = document.createElement('div');
        wrapper.className = 'flex gap-3 animate-slide-in ' + (role === 'user' ? 'justify-end' : '');

        if (role === 'user') {
            // 构建附件预览 HTML
            let attachHtml = '';
            if (attachments && attachments.length > 0) {
                const items = attachments.map(a => {
                    if (a.type === 'image' && a.url) {
                        return `<div class="mt-2"><img src="${escapeHtml(a.url)}" alt="${escapeHtml(a.name)}" class="max-w-xs max-h-48 rounded-lg border border-nocturne-border"></div>`;
                    }
                    const icon = a.type === 'image' ? 'image' : 'file-text';
                    return `<div class="flex items-center gap-2 mt-2 px-3 py-1.5 rounded-lg bg-nocturne-surface/60 border border-nocturne-border text-xs">
                        <i data-lucide="${icon}" class="w-3.5 h-3.5 text-nocturne-mint flex-shrink-0"></i>
                        <span class="truncate text-nocturne-text-muted">${escapeHtml(a.name)}</span>
                        <span class="text-nocturne-text-dim flex-shrink-0">${formatFileSize(a.size)}</span>
                    </div>`;
                }).join('');
                attachHtml = `<div class="mt-1">${items}</div>`;
            }
            const textHtml = content ? `<div class="message-content">${escapeHtml(content)}</div>` : '';
            wrapper.innerHTML = `
                <div class="max-w-[80%] px-5 py-3 rounded-2xl rounded-br-sm border border-nocturne-mint/30 bg-nocturne-mint/5 text-sm">
                    ${textHtml}${attachHtml}
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

    // ==================== 文件上传 ====================

    function updateSendButton() {
        const hasText = messageInput.value.length > 0;
        const hasReady = attachments.some(a => a.status === 'done');
        const hasUploading = attachments.some(a => a.status === 'uploading');
        sendButton.disabled = isStreaming || hasUploading || (!hasText && !hasReady);
    }

    function formatFileSize(bytes) {
        if (!bytes && bytes !== 0) return '';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    }

    async function handleFileUpload(file) {
        // 大小限制 10MB
        if (file.size > 10 * 1024 * 1024) {
            alert(`文件 ${file.name} 超过 10MB 限制`);
            return;
        }

        const id = ++attachmentIdSeq;
        const placeholder = {
            id,
            name: file.name,
            type: file.type.startsWith('image/') ? 'image' : 'file',
            size: file.size,
            content: '',
            url: '',
            status: 'uploading',
        };
        attachments.push(placeholder);
        renderAttachmentsPreview();
        updateSendButton();

        const formData = new FormData();
        formData.append('file', file);

        try {
            const resp = await fetch('/chat/api/upload/', {
                method: 'POST',
                body: formData,
            });
            const data = await resp.json();
            if (!resp.ok || !data.success) {
                const err = (data && data.error) || `上传失败 (${resp.status})`;
                removeAttachment(id);
                alert(`上传失败: ${err}`);
                return;
            }
            const idx = attachments.findIndex(a => a.id === id);
            if (idx === -1) return; // 已被移除
            attachments[idx] = {
                id,
                name: data.name,
                type: data.type,
                size: data.size,
                content: data.content || '',
                url: data.url || '',
                status: 'done',
            };
            renderAttachmentsPreview();
            updateSendButton();
        } catch (err) {
            removeAttachment(id);
            alert(`上传失败: ${err.message}`);
            console.error(err);
        }
    }

    function removeAttachment(id) {
        attachments = attachments.filter(a => a.id !== id);
        renderAttachmentsPreview();
        updateSendButton();
    }

    function renderAttachmentsPreview() {
        if (!attachmentsPreview) return;
        if (attachments.length === 0) {
            attachmentsPreview.classList.add('hidden');
            attachmentsPreview.innerHTML = '';
            return;
        }
        attachmentsPreview.classList.remove('hidden');
        attachmentsPreview.innerHTML = attachments.map(a => {
            if (a.type === 'image' && a.url && a.status === 'done') {
                return `<div class="relative group">
                    <img src="${escapeHtml(a.url)}" alt="${escapeHtml(a.name)}" class="w-16 h-16 object-cover rounded-lg border border-nocturne-border">
                    <button type="button" data-remove-attach="${a.id}" class="absolute -top-1.5 -right-1.5 w-5 h-5 flex items-center justify-center rounded-full bg-nocturne-elevated border border-nocturne-border text-nocturne-text-muted hover:text-red-400 hover:border-red-400/50 transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>`;
            }
            const icon = a.type === 'image' ? 'image' : 'file-text';
            const statusBadge = a.status === 'uploading'
                ? `<span class="text-nocturne-amber text-[10px] font-mono">上传中…</span>`
                : `<span class="text-nocturne-text-dim text-[10px] font-mono">${formatFileSize(a.size)}</span>`;
            return `<div class="relative group flex items-center gap-2 px-3 py-1.5 rounded-lg bg-nocturne-surface/60 border border-nocturne-border text-xs max-w-[220px]">
                <i data-lucide="${icon}" class="w-3.5 h-3.5 text-nocturne-mint flex-shrink-0"></i>
                <div class="flex flex-col min-w-0">
                    <span class="truncate text-nocturne-text-muted">${escapeHtml(a.name)}</span>
                    ${statusBadge}
                </div>
                <button type="button" data-remove-attach="${a.id}" class="flex-shrink-0 ml-1 w-4 h-4 flex items-center justify-center text-nocturne-text-dim hover:text-red-400 transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
            </div>`;
        }).join('');

        // 绑定移除按钮
        attachmentsPreview.querySelectorAll('[data-remove-attach]').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.getAttribute('data-remove-attach'), 10);
                removeAttachment(id);
            });
        });

        if (window.lucide) lucide.createIcons();
    }

    // ==================== 启动 ====================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
