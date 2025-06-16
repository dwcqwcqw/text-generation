// 强制修复MIME类型问题的脚本
console.log('🔧 MIME类型修复脚本开始运行');

// 立即执行的函数，无需等待DOM加载
(function() {
  // 1. 修复现有的script标签
  function fixExistingScripts() {
    const scripts = document.querySelectorAll('script[src]:not([type="application/javascript"])');
    console.log(`🔍 找到 ${scripts.length} 个需要修复的脚本标签`);
    
    scripts.forEach((script, index) => {
      if (!script.src.includes('fix-mime.js')) {
        console.log(`✅ 修复脚本 ${index + 1}: ${script.src}`);
        script.setAttribute('type', 'application/javascript');
      }
    });
  }

  // 2. 重写document.createElement 来确保新创建的script标签有正确的type
  const originalCreateElement = document.createElement.bind(document);
  document.createElement = function(tagName, options) {
    const element = originalCreateElement(tagName, options);
    if (tagName.toLowerCase() === 'script' && !element.type) {
      element.type = 'application/javascript';
    }
    return element;
  };

  // 3. 立即修复现有脚本
  fixExistingScripts();

  // 4. 监听DOM变化，修复动态添加的脚本
  if (typeof MutationObserver !== 'undefined') {
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        mutation.addedNodes.forEach(function(node) {
          if (node.nodeType === 1) { // Element node
            if (node.tagName === 'SCRIPT' && node.src && !node.type) {
              console.log('🔧 修复动态添加的脚本:', node.src);
              node.type = 'application/javascript';
            }
            // 也检查子元素
            const scripts = node.querySelectorAll && node.querySelectorAll('script[src]:not([type])');
            if (scripts) {
              scripts.forEach(script => {
                console.log('🔧 修复子脚本:', script.src);
                script.type = 'application/javascript';
              });
            }
          }
        });
      });
    });

    observer.observe(document, {
      childList: true,
      subtree: true
    });
  }

  // 5. 在DOM加载完成后再次检查
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      setTimeout(fixExistingScripts, 100);
    });
  }

  // 6. 在窗口加载完成后最后检查一次
  window.addEventListener('load', function() {
    setTimeout(fixExistingScripts, 200);
  });

  console.log('✅ MIME类型修复脚本初始化完成');
})(); 