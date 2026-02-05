# macOS Permissions Setup

OpenClaw Voice Hotkey потребує спеціальних дозволів macOS для роботи з hotkeys та мікрофоном.

## ⚠️ Важливо: Accessibility Access

Без цього дозволу hotkey (`Cmd+Shift+Space`) **не буде працювати**.

### Помилка

Якщо бачиш:
```
This process is not trusted! Input event monitoring will not be possible 
until it is added to accessibility clients.
```

### Рішення

1. Відкрий **System Settings** (Системні налаштування)
2. Перейди до **Privacy & Security** → **Accessibility**
3. Натисни 🔒 (lock icon) і введи пароль
4. Натисни **+** (плюс) щоб додати додаток
5. Додай **Terminal** (або iTerm2, якщо використовуєш його):
   - Знайди `/Applications/Utilities/Terminal.app`
   - Або `/Applications/iTerm.app`
6. Постав галочку ✅ навпроти Terminal
7. Перезапусти assistant

### Альтернатива: Запуск як standalone app

Якщо не хочеш давати доступ Terminal:

```bash
# Створити standalone .app bundle
# (TODO: буде додано пізніше)
```

---

## 🎤 Microphone Access

При першому запуску macOS запитає дозвіл на мікрофон.

**Якщо відмовив:**

1. **System Settings** → **Privacy & Security** → **Microphone**
2. Увімкни **Terminal** (або iTerm2)
3. Перезапусти assistant

---

## ✅ Перевірка дозволів

Після налаштування:

```bash
cd ~/work/openclaw-voice-hotkey
./run.sh
```

Має з'явитись:
```
🎙️  OpenClaw Voice Hotkey Assistant
📍 Gateway: ws://127.0.0.1:18789
🔑 Hotkey: cmd+shift+space
Press Cmd+Shift+Space to record, Escape to exit
```

**Без помилки** "This process is not trusted!"

---

## 🐛 Debug

Якщо hotkey не спрацьовує:

1. **Перевір Accessibility:**
   ```bash
   # У Terminal
   osascript -e 'tell application "System Events" to keystroke "a"'
   ```
   
   Якщо помилка → Accessibility не налаштований.

2. **Тестовий hotkey:**
   Натисни `Cmd+Shift+Space` → має з'явитись:
   ```
   🎤 Hotkey detected: Cmd+Shift+Space
   🎤 Recording started...
   ```

3. **Перевір мікрофон:**
   ```bash
   # Записати тестове аудіо
   rec test.wav trim 0 3
   
   # Відтворити
   play test.wav
   ```

---

## 📸 Скріншоти

### Accessibility Settings

![Accessibility](https://support.apple.com/library/content/dam/edam/applecare/images/en_US/macos/Big-Sur/macos-big-sur-system-preferences-security-privacy-accessibility.jpg)

✅ Terminal має бути в списку з галочкою

### Microphone Settings

Аналогічно в **Privacy & Security** → **Microphone**

---

## ❓ FAQ

**Q: Чому потрібен Accessibility access?**  
A: macOS блокує доступ до global hotkeys для безпеки. Без цього дозволу процес не може "слухати" комбінації клавіш.

**Q: Це безпечно?**  
A: Так. Ти даєш дозвіл тільки Terminal/iTerm2, не всім додаткам. Код відкритий і не робить нічого крім запису аудіо при натисканні hotkey.

**Q: Можна без Accessibility?**  
A: Можна використати альтернативні методи (Shortcuts.app, Automator), але вони складніші в налаштуванні.

**Q: Hotkey не працює навіть з дозволом?**  
A: Спробуй:
1. Повністю закрити Terminal
2. Відкрити знову
3. Запустити `./run.sh`

Або перезавантажити Mac (іноді macOS кешує дозволи).
