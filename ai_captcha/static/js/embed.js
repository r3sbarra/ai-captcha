/**
 * AI CAPTCHA — host-side embed helper.
 *
 * Drop-in integration for the iframe widget, reCAPTCHA-style ergonomics:
 *
 *   <div class="ai-captcha" data-sitekey="YOUR_SITEKEY"
 *        data-callback="onCaptchaPass" data-error-callback="onCaptchaError"></div>
 *   <script src="https://YOUR_HOST/apps/ai-captcha/static/js/embed.js" async defer></script>
 *
 * The helper:
 *   - creates the iframe pointing at /embed?sitekey=...&origin=<host origin>
 *   - listens for postMessage from the widget (strict origin + source checks)
 *   - on pass, stores the token in a hidden input `ai-captcha-response` and
 *     calls the `data-callback` (or `window[data-callback]`) with the token
 *   - on fail/error, calls the `data-error-callback`
 *
 * SECURITY: the token in the hidden field / callback is a CLAIM, not proof.
 * Your backend MUST call POST /api/siteverify with your secretkey before
 * trusting it. Never grant access based on the client-side token alone.
 */
(function () {
  'use strict';

  function findWidgets() {
    return Array.prototype.slice.call(
      document.querySelectorAll('.ai-captcha[data-sitekey]')
    );
  }

  function getOrigin() {
    return window.location.origin;
  }

  function mount(widget) {
    var sitekey = widget.getAttribute('data-sitekey');
    var tier = widget.getAttribute('data-tier') || 'medium';
    var width = widget.getAttribute('data-width') || '100%';
    var height = widget.getAttribute('data-height') || '220';
    var callback = widget.getAttribute('data-callback');
    var errorCallback = widget.getAttribute('data-error-callback');
    var base = widget.getAttribute('data-base') || '/apps/ai-captcha';

    // Hidden field to carry the token with a form submit.
    var hidden = document.createElement('input');
    hidden.type = 'hidden';
    hidden.name = 'ai-captcha-response';
    hidden.id = 'ai-captcha-response-' + sitekey;
    widget.appendChild(hidden);

    var iframe = document.createElement('iframe');
    iframe.setAttribute('frameborder', '0');
    iframe.setAttribute('scrolling', 'no');
    iframe.style.width = width;
    iframe.style.height = height;
    iframe.style.border = '0';
    iframe.setAttribute('loading', 'lazy');
    iframe.src = base + '/embed?sitekey=' + encodeURIComponent(sitekey) +
      '&origin=' + encodeURIComponent(getOrigin()) +
      '&tier=' + encodeURIComponent(tier);
    widget.appendChild(iframe);

    var widgetOrigin = null;
    try { widgetOrigin = new URL(iframe.src).origin; } catch (e) {}

    function invoke(name, arg) {
      if (!name) return;
      var fn = window[name];
      if (typeof fn === 'function') { try { fn(arg); } catch (e) {} }
    }

    window.addEventListener('message', function (event) {
      // 1. Origin allow-list — must match the widget's exact origin.
      if (widgetOrigin && event.origin !== widgetOrigin) return;
      // 2. Source identity — only accept from this widget's iframe.
      if (event.source !== iframe.contentWindow) return;
      var d = event.data;
      // 3. Schema/version validation.
      if (!d || d.source !== 'ai-captcha' || d.version !== 1) return;

      switch (d.type) {
        case 'pass':
          hidden.value = d.token || '';
          invoke(callback, d.token);
          break;
        case 'fail':
        case 'error':
          hidden.value = '';
          invoke(errorCallback, d.reason || d.type);
          break;
        case 'resize':
          if (d.height) iframe.style.height = Math.min(Number(d.height) || 0, 600) + 'px';
          break;
        default:
          break;
      }
    });
  }

  function init() {
    findWidgets().forEach(mount);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
