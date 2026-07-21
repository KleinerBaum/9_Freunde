import { PDFDocument, StandardFonts, rgb, type PDFFont, type PDFPage } from "pdf-lib";

import type { Child, ManagedDocument, Parent } from "./contracts";

const formatMoney = (cents: number) =>
  new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(cents / 100);

function drawWrappedText(
  page: PDFPage,
  text: string,
  options: { x: number; y: number; maxWidth: number; size: number; font: PDFFont; color?: ReturnType<typeof rgb>; lineHeight?: number }
) {
  const words = text.split(/\s+/u);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (options.font.widthOfTextAtSize(candidate, options.size) <= options.maxWidth) {
      current = candidate;
    } else {
      if (current) lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  const lineHeight = options.lineHeight ?? options.size * 1.45;
  lines.forEach((line, index) => page.drawText(line, {
    x: options.x,
    y: options.y - index * lineHeight,
    size: options.size,
    font: options.font,
    color: options.color ?? rgb(0.16, 0.15, 0.13)
  }));
  return options.y - lines.length * lineHeight;
}

export async function buildManagedDocumentPdf(
  document: ManagedDocument,
  child: Child,
  parent: Parent | undefined
): Promise<Uint8Array> {
  const pdf = await PDFDocument.create();
  const page = pdf.addPage([595.28, 841.89]);
  const regular = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const muted = rgb(0.42, 0.39, 0.34);
  const accent = rgb(0.89, 0.31, 0.2);

  page.drawRectangle({ x: 0, y: 0, width: 595.28, height: 841.89, color: rgb(0.99, 0.98, 0.95) });
  page.drawRectangle({ x: 0, y: 786, width: 595.28, height: 56, color: rgb(0.98, 0.73, 0.22) });
  page.drawText("9", { x: 42, y: 797, size: 32, font: bold, color: rgb(0.8, 0.18, 0.12) });
  page.drawText("FREUNDE", { x: 69, y: 806, size: 16, font: bold, color: rgb(0.25, 0.15, 0.11) });
  page.drawText("Kinderbetreuung mit Liebe", { x: 69, y: 793, size: 8.5, font: regular, color: rgb(0.35, 0.22, 0.16) });

  let y = 744;
  page.drawText(document.type === "invoice" ? "MONATSABRECHNUNG" : "BETREUUNGSVERTRAG · ENTWURF", {
    x: 42, y, size: 10, font: bold, color: accent
  });
  y -= 35;
  page.drawText(document.title, { x: 42, y, size: 24, font: bold, color: rgb(0.13, 0.12, 0.11) });
  y -= 24;
  page.drawText(`${document.number}  ·  Erstellt am ${document.createdAt}`, { x: 42, y, size: 9, font: regular, color: muted });
  y -= 46;

  const details = [
    ["Kind", child.name],
    ["Vertragspartner", parent?.name ?? child.primaryParentEmail],
    ["Zeitraum", document.period],
    ["Fällig am", document.dueDate]
  ];
  details.forEach(([label, value], index) => {
    const x = 42 + (index % 2) * 255;
    const rowY = y - Math.floor(index / 2) * 50;
    page.drawText(label ?? "", { x, y: rowY, size: 8.5, font: bold, color: muted });
    page.drawText(value ?? "—", { x, y: rowY - 17, size: 11, font: regular, color: rgb(0.16, 0.15, 0.13) });
  });
  y -= 124;

  if (document.type === "invoice") {
    page.drawRectangle({ x: 42, y: y - 8, width: 511, height: 34, color: rgb(0.96, 0.93, 0.87) });
    page.drawText("LEISTUNG", { x: 56, y: y + 3, size: 8, font: bold, color: muted });
    page.drawText("BETRAG", { x: 455, y: y + 3, size: 8, font: bold, color: muted });
    y -= 34;
    [["Betreuungspauschale", document.careFeeCents], ["Verpflegungspauschale", document.mealFeeCents]].forEach(([label, amount]) => {
      page.drawText(String(label), { x: 56, y, size: 11, font: regular });
      page.drawText(formatMoney(Number(amount)), { x: 455, y, size: 11, font: regular });
      page.drawLine({ start: { x: 56, y: y - 12 }, end: { x: 539, y: y - 12 }, thickness: 0.5, color: rgb(0.85, 0.82, 0.77) });
      y -= 34;
    });
    page.drawText("Gesamt", { x: 360, y: y - 2, size: 12, font: bold });
    page.drawText(formatMoney(document.totalCents), { x: 455, y: y - 2, size: 12, font: bold, color: accent });
    y -= 62;
    y = drawWrappedText(page, "Bitte überweisen Sie den Betrag unter Angabe der Rechnungsnummer. Diese Demo enthält bewusst keine Bank- oder Personendaten.", {
      x: 42, y, maxWidth: 511, size: 10, font: regular, color: muted
    });
  } else {
    const paragraphs = [
      `Zwischen 9 Freunde und ${parent?.name ?? "dem/der Sorgeberechtigten"} wird für ${child.name} ab ${child.careStart || "dem vereinbarten Startdatum"} eine Betreuung im Umfang von ${child.careHoursPerWeek} Stunden pro Woche vereinbart.`,
      `Die monatliche Verpflegungspauschale beträgt ${formatMoney(child.mealFeeCents)}. Weitere öffentlich-rechtliche Beiträge oder Förderbedingungen sind nicht Bestandteil dieses Entwurfs.`,
      "Foto- und Download-Einwilligungen werden separat dokumentiert. Widerrufe wirken für zukünftige Verarbeitungen und müssen von der Leitung nachvollziehbar erfasst werden.",
      "Dieser automatisch erzeugte Vertrag ist ein Arbeitsentwurf. Er ersetzt keine rechtliche Prüfung und wird erst nach Prüfung, Ergänzung und Unterschrift verbindlich."
    ];
    for (const paragraph of paragraphs) {
      y = drawWrappedText(page, paragraph, { x: 42, y, maxWidth: 511, size: 10.5, font: regular, lineHeight: 16 });
      y -= 18;
    }
    page.drawLine({ start: { x: 42, y: 158 }, end: { x: 250, y: 158 }, thickness: 0.7, color: muted });
    page.drawLine({ start: { x: 345, y: 158 }, end: { x: 553, y: 158 }, thickness: 0.7, color: muted });
    page.drawText("Ort, Datum · Sorgeberechtigte", { x: 42, y: 140, size: 8, font: regular, color: muted });
    page.drawText("Ort, Datum · 9 Freunde", { x: 345, y: 140, size: 8, font: regular, color: muted });
  }

  page.drawText("Vertraulich · nur für berechtigte Empfänger:innen", { x: 42, y: 36, size: 8, font: regular, color: muted });
  page.drawText("Seite 1 / 1", { x: 500, y: 36, size: 8, font: regular, color: muted });
  return pdf.save();
}
