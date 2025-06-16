// 这个脚本用于修复MIME类型问题
console.log('MIME类型修复脚本已加载');

// 动态加载JavaScript文件的函数
function loadScript(url, callback) {
  const script = document.createElement('script');
  script.type = 'application/javascript';
  script.src = url;
  script.async = true;
  script.onload = callback;
  script.onerror = (error) => {
    console.error('脚本加载失败:', url, error);
    // 尝试重新加载
    setTimeout(() => {
      console.log('尝试重新加载脚本:', url);
      loadScript(url, callback);
    }, 1000);
  };
  document.head.appendChild(script);
}

// 动态加载CSS文件的函数
function loadCSS(url) {
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.type = 'text/css';
  link.href = url;
  link.onload = () => console.log('CSS加载成功:', url);
  link.onerror = (error) => {
    console.error('CSS加载失败:', url, error);
  };
  document.head.appendChild(link);
}

// 检查并修复MIME类型
function fixMimeTypes() {
  console.log('开始修复MIME类型问题');
  
  // 获取所有脚本标签
  const scripts = document.querySelectorAll('script[src]');
  const loadedScripts = new Set();
  
  scripts.forEach(script => {
    if (script.src && !script.src.includes('fix-mime.js') && !loadedScripts.has(script.src)) {
      loadedScripts.add(script.src);
      console.log('重新加载脚本:', script.src);
      loadScript(script.src, () => {
        console.log('脚本加载完成:', script.src);
      });
    }
  });
  
  // 检查CSS文件
  const cssLinks = document.querySelectorAll('link[rel="stylesheet"]');
  cssLinks.forEach(link => {
    if (link.href && !link.sheet) {
      console.log('重新加载CSS:', link.href);
      loadCSS(link.href);
    }
  });
}

// 在页面加载完成后执行
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', fixMimeTypes);
} else {
  fixMimeTypes();
}

// 也在window.onload时执行，确保所有资源都被处理
window.addEventListener('load', () => {
  console.log('页面完全加载，再次检查MIME类型');
  setTimeout(fixMimeTypes, 500);
}); 