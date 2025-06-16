// 这个脚本用于修复MIME类型问题
console.log('MIME类型修复脚本已加载');

// 动态加载JavaScript文件的函数
function loadScript(url, callback) {
  const script = document.createElement('script');
  script.type = 'application/javascript';
  script.src = url;
  script.onload = callback;
  script.onerror = (error) => {
    console.error('脚本加载失败:', url, error);
  };
  document.head.appendChild(script);
}

// 在页面加载完成后执行
window.addEventListener('DOMContentLoaded', () => {
  console.log('页面加载完成，开始修复MIME类型问题');
  
  // 获取所有已有的脚本标签
  const scripts = document.querySelectorAll('script[src]');
  
  // 记录需要重新加载的脚本
  const scriptsToReload = [];
  
  // 收集所有外部脚本的URL
  scripts.forEach(script => {
    if (script.src && !script.src.includes('fix-mime.js')) {
      scriptsToReload.push(script.src);
    }
  });
  
  console.log('需要重新加载的脚本:', scriptsToReload);
  
  // 依次加载所有脚本
  let index = 0;
  function loadNextScript() {
    if (index < scriptsToReload.length) {
      loadScript(scriptsToReload[index], () => {
        index++;
        loadNextScript();
      });
    } else {
      console.log('所有脚本重新加载完成');
    }
  }
  
  // 开始加载第一个脚本
  loadNextScript();
}); 