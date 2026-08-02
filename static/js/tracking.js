/**
 * 轻量埋点：页面 PV 自动上报 + data-track 属性自动绑定点击事件
 *
 * 用法：
 *   <button data-track="chat_send" data-track-payload='{"type":"text"}'>发送</button>
 *   window.trackEvent("douyin_crawl", {source: "page"});
 */
(function () {
    var TRACK_URL = '/api/track/';

    function send(eventType, eventName, pageUrl, payload) {
        var body = JSON.stringify({
            event_type: eventType,
            event_name: eventName,
            page_url: pageUrl || (location.pathname + location.search),
            payload: payload || {}
        });
        if (navigator.sendBeacon) {
            navigator.sendBeacon(TRACK_URL, new Blob([body], { type: 'application/json' }));
        } else {
            fetch(TRACK_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: body,
                keepalive: true
            }).catch(function () {});
        }
    }

    window.trackEvent = function (name, payload) {
        send('action', name, null, payload);
    };

    document.addEventListener('DOMContentLoaded', function () {
        // 页面访问
        send('pageview', 'pageview', location.pathname + location.search);

        // 自动绑定 data-track 元素
        document.querySelectorAll('[data-track]').forEach(function (el) {
            el.addEventListener('click', function () {
                var payload = {};
                try {
                    payload = JSON.parse(el.dataset.trackPayload || '{}');
                } catch (e) { /* 忽略非法 JSON */ }
                send('click', el.dataset.track, location.pathname, payload);
            });
        });
    });
})();
