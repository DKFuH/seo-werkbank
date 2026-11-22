import { useQuery } from "@tanstack/react-query";
import { Share2 } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Button, ErrorBox, Field, Input, Spinner } from "../components/ui";
import { api, errorMessage } from "../lib/api";
import { useAuth } from "../lib/context";

export default function Login() {
  const { login, register } = useAuth();
  const { data: status, isLoading, error: statusError } = useQuery({ queryKey: ["auth-status"], queryFn: () => api.get("/auth/status"), retry: false });
  const [mode, setMode] = useState<"login" | "register" | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <Spinner label="Verbinde…" />;
  const firstRun = status && !status.has_users;
  const active = mode ?? (firstRun ? "register" : "login");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await (active === "register" ? register(email, password) : login(email, password));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4 dark:bg-slate-950">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600 text-white"><Share2 className="h-5 w-5" /></span>
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">SEO-Werkbank</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {firstRun ? "Willkommen. Lege das Administratorkonto für diese Installation an." : active === "register" ? "Konto anlegen" : "Anmelden"}
          </p>
        </div>
        <form onSubmit={submit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          {statusError ? <ErrorBox error={statusError} /> : null}
          {error && <ErrorBox error={error} />}
          <Field label="E-Mail">
            <Input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="du@example.de" />
          </Field>
          <Field label="Passwort" hint={active === "register" ? "Mindestens 8 Zeichen. Wird als Argon2id-Hash gespeichert." : undefined}>
            <Input type="password" autoComplete={active === "register" ? "new-password" : "current-password"} required
              minLength={active === "register" ? 8 : 1} value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Button type="submit" variant="primary" loading={busy} className="w-full">{active === "register" ? "Konto anlegen" : "Anmelden"}</Button>
          {!firstRun && status?.registration_open && (
            <button type="button" className="block w-full text-center text-xs text-brand-700 hover:underline dark:text-brand-300"
              onClick={() => { setMode(active === "login" ? "register" : "login"); setError(null); }}>
              {active === "login" ? "Noch kein Konto? Registrieren" : "Schon registriert? Anmelden"}
            </button>
          )}
        </form>
        <p className="mt-4 text-center text-xs text-slate-500 dark:text-slate-400">Kostenlos und Open Source. Deine Daten bleiben auf diesem Rechner.</p>
      </div>
    </div>
  );
}
