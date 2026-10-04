import { FormEvent, useEffect, useState } from "react";
import { clearTokens, getAccessToken, getMe, login, register } from "./api";
import Dashboard from "./Dashboard";

type User = { id: number; username: string; email: string; is_staff: boolean };

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(getAccessToken()));
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getAccessToken()) return;
    getMe()
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="center-screen">Загрузка системы…</div>;

  if (user) {
    return (
      <Dashboard
        user={user}
        onLogout={() => {
          clearTokens();
          setUser(null);
        }}
      />
    );
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    const username = String(data.get("username") || "");
    const password = String(data.get("password") || "");
    const email = String(data.get("email") || "");

    try {
      if (mode === "register") await register(username, email, password);
      else await login(username, password);
      setUser(await getMe());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось выполнить вход");
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-hero">
        <span className="eyebrow">МАГИСТЕРСКАЯ РАБОТА</span>
        <h1>Геоинформационная система оценки социальной инфраструктуры</h1>
        <p>
          Анализ нормативной доступности школ, детских садов, медицины,
          транспорта, торговли и спортивных объектов.
        </p>
      </section>

      <form className="auth-card" onSubmit={submit}>
        <h2>{mode === "login" ? "Вход в систему" : "Регистрация"}</h2>
        <label>
          Логин
          <input name="username" required autoComplete="username" />
        </label>
        {mode === "register" && (
          <label>
            Электронная почта
            <input name="email" type="email" autoComplete="email" />
          </label>
        )}
        <label>
          Пароль
          <input name="password" type="password" minLength={8} required autoComplete={mode === "login" ? "current-password" : "new-password"} />
        </label>
        {error && <div className="error">{error}</div>}
        <button type="submit">{mode === "login" ? "Войти" : "Создать аккаунт"}</button>
        <button
          className="link-button"
          type="button"
          onClick={() => {
            setError("");
            setMode(mode === "login" ? "register" : "login");
          }}
        >
          {mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
        </button>
      </form>
    </main>
  );
}
