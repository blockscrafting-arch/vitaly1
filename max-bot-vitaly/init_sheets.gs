// Скрипт для Google Таблиц для создания структуры бота napitki133.ru (ТЗ v2.0)
// Инструкция:
// 1. Откройте Google Таблицы: https://docs.google.com/spreadsheets/
// 2. Создайте новую пустую таблицу.
// 3. В меню выберите: Расширения -> Apps Script.
// 4. Удалите весь код в открывшемся окне и вставьте этот скрипт.
// 5. Нажмите кнопку "Сохранить" (значок дискеты).
// 6. Выберите функцию initBotSheets (вверху рядом с кнопкой "Выполнить").
// 7. Нажмите "Выполнить" (предоставьте необходимые разрешения при запросе).

function initBotSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // 1. Лист "Маппинг"
  let wsMapping = ss.getSheetByName("Маппинг");
  if (!wsMapping) {
    wsMapping = ss.insertSheet("Маппинг");
  }
  setupSheet(wsMapping, ["Категория", "Канал"], [
    ["путеводител", "travel"],
    ["тайланд", "travel"],
    ["библиотека", "travel"],
    ["лайфхак", "lifhaki"],
    ["напитк", "drinks"],
    ["виски", "drinks"],
    ["джин", "drinks"],
    ["ром", "drinks"],
    ["водка", "drinks"],
    ["вино", "drinks"],
    ["пиво", "drinks"],
    ["коктейл", "drinks"],
    ["кофе", "drinks"],
    ["чай", "drinks"],
  ]);

  // 2. Лист "История"
  let wsHistory = ss.getSheetByName("История");
  if (!wsHistory) {
    wsHistory = ss.insertSheet("История");
  }
  setupSheet(wsHistory, ["Дата", "URL", "Платформа", "Канал", "Текст (превью)"], []);
  
  // 3. Лист "Расписание"
  let wsSchedule = ss.getSheetByName("Расписание");
  if (!wsSchedule) {
    wsSchedule = ss.insertSheet("Расписание");
  }
  setupSheet(wsSchedule, ["Канал", "Тип", "День", "Время"], [
    ["travel", "main", "*", "04:00"],
    ["travel", "main", "*", "16:00"],
    ["lifhaki", "main", "*", "08:00"],
    ["lifhaki", "main", "*", "20:00"],
    ["drinks", "main", "*", "06:00"],
    ["drinks", "main", "*", "18:00"],
    
    ["travel", "shop", "fri", "11:30"],
    ["drinks", "shop", "fri", "12:30"],
    ["lifhaki", "shop", "fri", "17:30"],
    
    ["travel", "cross", "mon", "11:30"],
    ["lifhaki", "cross", "tue", "13:30"],
    
    ["travel", "site", "wed", "11:30"],
    ["drinks", "site", "wed", "12:30"],
    ["lifhaki", "site", "thu", "13:30"],
    
    ["travel", "radio", "thu", "19:00"],
    ["drinks", "radio", "sun", "20:30"],
    
    ["*", "rotation", "sat", "15:00"]
  ]);

  // 4. Лист "Промпты"
  let wsPrompts = ss.getSheetByName("Промпты");
  if (!wsPrompts) {
    wsPrompts = ss.insertSheet("Промпты");
  }
  setupSheet(wsPrompts, ["Ключ", "Текст"], [
    ["main_travel", "Ты — редактор канала о путешествиях. По материалу с сайта напиши короткий пост для соцсети (2–4 предложения).\nСтруктура: сильный заход про место, короткий факт/маршрут/сценарий, зачем открыть материал. В конце — призыв перейти по ссылке (ссылку не пиши, её подставят).\nПравила: без восклицаний, капслока и нагромождения эмодзи. Только текст, без markdown."],
    ["main_lifhaki", "Ты — редактор канала про лайфхаки. По материалу с сайта напиши короткий пост (2–4 предложения).\nСтруктура: ошибка/ловушка/польза, решение, зачем открыть. В конце — призыв перейти по ссылке (ссылку не пиши).\nПравила: без восклицаний и капслока. Только текст."],
    ["main_drinks", "Ты — редактор канала о напитках. По материалу с сайта напиши короткий пост (2–4 предложения).\nСтруктура: вкус/стиль/напиток, один факт или образ, зачем открыть. В конце — призыв перейти по ссылке (ссылку не пиши).\nПравила: без восклицаний и капслока. Только текст."],
    ["shop", "Ты — редактор. Опиши книгу/материал из магазина: что это, кому пригодится, чем полезно. 2–4 предложения. В конце — призыв перейти в магазин (ссылку не пиши). Без восклицаний и капслока."],
    ["radio", "Ты — редактор. Напиши короткий атмосферный пост про радио сайта: настроение (вечер, дорога, работа, кофе, дождь — выбери одно), когда включить, зачем перейти. 2–3 предложения. Ссылку не пиши. Без восклицаний."],
    ["cross", "Ты — редактор. Напиши нативный анонс другого канала для подписчиков: кому зайдёт, почему стоит перейти. Без слов «подпишитесь» и без восклицаний. 2–3 предложения."],
    ["site", "Ты — редактор. Напиши мягкий пост про сайт napitki133.ru в целом: что там найдёшь, зачем зайти. 2–3 предложения. Ссылку не пиши. Без восклицаний."]
  ]);

  // 5. Лист "Настройки"
  let wsSettings = ss.getSheetByName("Настройки");
  if (!wsSettings) {
    wsSettings = ss.insertSheet("Настройки");
  }
  setupSheet(wsSettings, ["Ключ", "Значение"], [
    ["repeat_interval_days", "14"],
    ["shop_repeat_days", "21"],
    ["ad_min_interval_days", "6"],
    ["selection_mode", "hybrid"],
    ["text_repeat_limit", "50"],
    ["subcategory_gap", "true"]
  ]);

  // Удаляем дефолтный "Лист 1", если он пустой и мы создали другие
  const defaultSheet = ss.getSheetByName("Лист 1") || ss.getSheetByName("Sheet1");
  if (defaultSheet && ss.getSheets().length > 1 && defaultSheet.getLastRow() === 0) {
    ss.deleteSheet(defaultSheet);
  }

  SpreadsheetApp.getUi().alert("Таблица успешно инициализирована!");
}

function setupSheet(sheet, headers, data) {
  // 1. Очистка ВСЕГО листа: данных, форматов и ПРАВИЛ ПРОВЕРКИ
  sheet.clear();
  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).clearDataValidations();
  
  // Установка заголовков
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setValues([headers]);
  headerRange.setFontWeight("bold");
  headerRange.setBackground("#f3f3f3");
  
  // Добавление данных
  if (data && data.length > 0) {
    sheet.getRange(2, 1, data.length, data[0].length).setValues(data);
  }
  
  // Автоматическая ширина колонок
  for (let i = 1; i <= headers.length; i++) {
    sheet.autoResizeColumn(i);
  }
  
  // Закрепление верхней строки
  sheet.setFrozenRows(1);
}
