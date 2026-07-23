// Вариант 2 — собрать немецкие названия прямо со страницы
// Откройте указанную страницу, нажмите F12 → Console и вставьте:
// https://www.cardmarket.com/de/Pokemon/Products/Singles/Ascended-Heroes?idRarity=0&sortBy=collectorsnumber_asc&site=3&perSite=100
// максимум выводится 100 карточек, меняем site=(1,2,3,...) и оставляем perSite=100


(() => {
  const setName = "Ascended Heroes";

  const cards = [...document.querySelectorAll(
    'a[href*="/Pokemon/Products/Singles/Ascended-Heroes/"]'
  )]
    .map(link => {
      const text = link.textContent
        .replace(/\s+/g, " ")
        .trim();

      const match = text.match(
        /^(.*?)\s*\(([A-Za-z0-9]+)\s+([^)]+)\)/
      );

      if (!match) return null;

      return {
        card_name: match[1].trim(),
        set_name: setName,
        set_code: match[2].trim(),
        card_number: match[3].trim(),
        url: new URL(link.href, location.origin).href
      };
    })
    .filter(Boolean);

  const unique = [
    ...new Map(
      cards.map(card => [
        `${card.set_code}-${card.card_number}-${card.url}`,
        card
      ])
    ).values()
  ];

  const escapeCsv = value =>
    `"${String(value ?? "").replaceAll('"', '""')}"`;

  const columns = [
    "card_name",
    "set_name",
    "set_code",
    "card_number",
    "url"
  ];

  const csv = [
    columns.join(";"),
    ...unique.map(card =>
      columns.map(column => escapeCsv(card[column])).join(";")
    )
  ].join("\n");

  const blob = new Blob(
    ["\uFEFF" + csv],
    { type: "text/csv;charset=utf-8" }
  );

  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = downloadUrl;
  anchor.download = "ascended_heroes_de.csv";
  anchor.click();

  URL.revokeObjectURL(downloadUrl);

  console.table(unique);
  console.log(`Собрано карт: ${unique.length}`);
})();