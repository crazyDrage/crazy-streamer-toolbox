let fieldData;
let count = 0;
window.addEventListener('onWidgetLoad', function (obj) {
  fieldData = obj.detail.fieldData;
  const data = obj.detail.session.data;
  document.getElementById('name').innerText = data['follower-latest']['name'] || fieldData.emptyText;
  SE_API.store.get('count').then(kept => { count = (kept && kept.value) || 0; });
});
window.addEventListener('onEventReceived', function (obj) {
  const {listener, event} = obj.detail;
  if (listener === 'follower-latest') {
    document.getElementById('name').innerText = event.name;
    count++;
    SE_API.store.set('count', {value: count});
  } else if (listener === 'message') {
    const line = document.createElement('div');
    line.innerHTML = event.data.displayName + ': ' + event.renderedText;
    document.getElementById('log').appendChild(line);
  } else if (listener === 'event:test' && event.listener === 'widget-button' && event.field === 'clearLog') {
    document.getElementById('log').innerHTML = '';
  }
});
