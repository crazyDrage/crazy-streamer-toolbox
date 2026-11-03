// JS: what the widget does. It works like a StreamElements custom widget.
let fieldData;

// once, when the widget loads: the settings (fieldData) and what happened before (session)
window.addEventListener('onWidgetLoad', function (obj) {
  fieldData = obj.detail.fieldData;
});

// every event: obj.detail.listener says what it is, obj.detail.event holds its data
window.addEventListener('onEventReceived', function (obj) {
  const {listener, event} = obj.detail;
  if (listener === 'message') {
    // a chat message from any platform:
    //   event.service           the platform: twitch, youtube, rumble, fansly
    //   event.data.displayName  who wrote it
    //   event.data.displayColor their name colour ("" when they have none)
    //   event.data.text         the text as written
    //   event.renderedText      the text with emotes as pictures (safe to use as HTML)
    addLine(event.service, event.data.displayName, event.renderedText, event.data.displayColor);
  } else if (listener === 'follower-latest') {
    // also: subscriber-latest, cheer-latest, raid-latest, tip-latest (event.name, event.amount, ...)
    addLine('', event.name, 'followed!', '');
  }
});

function addLine(platform, name, html, color) {
  const line = document.createElement('div');
  line.className = 'line ' + platform;
  if (platform) {
    const tag = document.createElement('span');
    tag.className = 'platform';
    tag.textContent = platform;
    line.appendChild(tag);
  }
  const who = document.createElement('span');
  who.className = 'name';
  who.textContent = name + ': ';  // textContent: a name is shown as text, never run as HTML
  if (color) who.style.color = color;
  line.appendChild(who);
  const text = document.createElement('span');
  text.innerHTML = html;
  line.appendChild(text);
  const lines = document.getElementById('lines');
  lines.appendChild(line);
  while (lines.children.length > fieldData.maxLines) lines.firstChild.remove();
}
