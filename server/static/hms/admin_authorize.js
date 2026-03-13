(function() {
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function isOnChangeListForModel(appLabel, modelName) {
    // crude: check URL path contains admin/<appLabel>/<modelName>
    return window.location.pathname.indexOf('/admin/' + appLabel + '/' + modelName + '/') !== -1;
  }

  function insertAuthorizeButton() {
    // find admin object-tools area (header actions)
    var header = document.querySelector('.object-tools');
    if (!header) {
      // fallback: find submit-row
      header = document.querySelector('.change-list');
    }
    if (!header) return;

    // Avoid inserting multiple times
    if (document.getElementById('authorize-address-button')) return;

    var btn = document.createElement('a');
    btn.id = 'authorize-address-button';
    btn.className = 'button';
    btn.textContent = 'Authorize Address';
    btn.style.marginRight = '8px';
    btn.href = '#';

    btn.addEventListener('click', function(e) {
      e.preventDefault();
      var addr = window.prompt('Enter Ethereum address to authorize (0x...)');
      if (!addr) return;
      // send POST to admin authorize URL
      var csrftoken = getCookie('csrftoken');
      fetch('/admin/hms/authorize-address/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrftoken
        },
        body: 'address=' + encodeURIComponent(addr)
      }).then(function(resp) {
        if (resp.redirected) {
          window.location = resp.url;
          return;
        }
        return resp.text();
      }).then(function(text) {
        // If not redirected, reload to show messages
        window.location.reload();
      }).catch(function(err) {
        alert('Error authorizing address: ' + err);
      });
    });

    // Place button into object-tools list if possible
    var ul = header.querySelector('ul') || header;
    if (ul.tagName.toLowerCase() === 'ul') {
      var li = document.createElement('li');
      li.appendChild(btn);
      ul.insertBefore(li, ul.firstChild);
    } else {
      header.insertBefore(btn, header.firstChild);
    }
  }

  // Run on DOM ready
  document.addEventListener('DOMContentLoaded', function() {
    if (isOnChangeListForModel('hms', 'onchainaudit')) {
      insertAuthorizeButton();
    }
  });
})();
