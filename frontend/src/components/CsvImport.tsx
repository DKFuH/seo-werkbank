/* CSV import with a column-mapping step: pick a file, check which column feeds which field, then import.
   The backend suggests the mapping from known header names; anything can be reassigned or left out. */
import { useState } from "react";
import { api } from "../lib/api";
import { Badge, Button, ErrorBox, FileButton, Modal, Notice, Select } from "./ui";

export type ImportKind = "gsc" | "backlinks" | "citations" | "keywords";
export type ImportFields = { mapping: string; number_format?: string };
type Preview = {
  kind: ImportKind; rows: number; one_of: string[]; number_format: "de" | "en" | null;
  columns: { index: number; name: string; samples: string[] }[];
  fields: { key: string; label: string; required: boolean; suggested: number | null }[];
};

export function CsvImportButton({ kind, label = "CSV importieren", accept, loading, onImport }: {
  kind: ImportKind; label?: string; accept?: string; loading?: boolean;
  onImport: (file: File, fields: ImportFields) => Promise<unknown>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [mapping, setMapping] = useState<Record<string, number | null>>({});
  const [numberFormat, setNumberFormat] = useState("auto");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const choose = async (f: File) => {
    setError(null);
    setBusy(true);
    try {
      const p: Preview = await api.upload("/imports/preview", f, { kind });
      setFile(f);
      setPreview(p);
      setMapping(Object.fromEntries(p.fields.map((x) => [x.key, x.suggested])));
      setNumberFormat(p.number_format ?? "auto");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const close = () => { setPreview(null); setFile(null); setError(null); };
  const missing = preview ? preview.fields.filter((f) => f.required && mapping[f.key] == null).map((f) => f.label) : [];
  const oneOfMissing = preview && preview.one_of.length > 0 && !preview.one_of.some((k) => mapping[k] != null);
  const used = Object.values(mapping).filter((v) => v != null);
  const duplicate = used.length !== new Set(used).size;
  const submit = async () => {
    if (!file || !preview) return;
    setError(null);
    setBusy(true);
    try {
      await onImport(file, { mapping: JSON.stringify(mapping), ...(preview.number_format ? { number_format: numberFormat } : {}) });
      close();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <FileButton label={label} accept={accept} loading={busy && !preview || loading} onFile={choose} />
      {error != null && !preview && <div className="mt-2"><ErrorBox error={error} /></div>}
      <Modal open={!!preview} onClose={close} wide title={`Spalten zuordnen: ${file?.name ?? ""}`}
        footer={<>
          <Button onClick={close}>Abbrechen</Button>
          <Button variant="primary" loading={busy} disabled={missing.length > 0 || !!oneOfMissing} onClick={submit}>
            {preview ? `${preview.rows.toLocaleString("de-DE")} Zeilen importieren` : "Importieren"}
          </Button>
        </>}>
        {preview && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Für jedes Feld die passende Spalte der Datei wählen. Vorschläge stammen aus den Spaltennamen; nicht benötigte Felder auf „nicht importieren“ lassen.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-slate-500 dark:text-slate-400">
                  <tr><th className="py-1.5 pr-3 font-medium">Feld</th><th className="py-1.5 pr-3 font-medium">Spalte in der Datei</th><th className="py-1.5 font-medium">Beispielwerte</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {preview.fields.map((f) => {
                    const col = mapping[f.key] != null ? preview.columns[mapping[f.key] as number] : null;
                    return (
                      <tr key={f.key}>
                        <td className="py-2 pr-3 align-top">
                          <span className="font-medium text-slate-900 dark:text-slate-100">{f.label}</span>
                          {f.required && <span className="ml-1 text-red-600" title="Pflichtfeld">*</span>}
                          {preview.one_of.includes(f.key) && <Badge tone="gray" title="Mindestens eines dieser Felder ist nötig">eins davon</Badge>}
                        </td>
                        <td className="w-64 py-2 pr-3 align-top">
                          <Select aria-label={`Spalte für ${f.label}`} value={mapping[f.key] ?? ""}
                            onChange={(e) => setMapping({ ...mapping, [f.key]: e.target.value === "" ? null : Number(e.target.value) })}>
                            <option value="">— nicht importieren —</option>
                            {preview.columns.map((c) => <option key={c.index} value={c.index}>{c.name}</option>)}
                          </Select>
                        </td>
                        <td className="max-w-xs py-2 align-top text-xs text-slate-500 dark:text-slate-400">
                          {col ? (col.samples.length ? col.samples.map((v, i) => <div key={i} className="truncate" title={v}>{v}</div>) : "leer") : "–"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {preview.number_format && (
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-slate-600 dark:text-slate-300">Zahlenformat:</span>
                <div className="w-64"><Select aria-label="Zahlenformat" value={numberFormat} onChange={(e) => setNumberFormat(e.target.value)}>
                  <option value="de">Deutsch (1.234,5)</option>
                  <option value="en">Englisch (1,234.5)</option>
                  <option value="auto">automatisch nach Spaltennamen</option>
                </Select></div>
              </div>
            )}
            {missing.length > 0 && <Notice tone="warn">Pflichtfeld ohne Spalte: {missing.join(", ")}</Notice>}
            {oneOfMissing && <Notice tone="warn">Mindestens eines zuordnen: {preview.fields.filter((f) => preview.one_of.includes(f.key)).map((f) => f.label).join(", ")}</Notice>}
            {duplicate && <Notice tone="info">Eine Spalte ist mehreren Feldern zugeordnet. Das ist erlaubt, aber selten gewollt.</Notice>}
            {error != null && <ErrorBox error={error} />}
          </div>
        )}
      </Modal>
    </>
  );
}
