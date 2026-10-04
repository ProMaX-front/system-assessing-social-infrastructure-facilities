import { FormEvent, useEffect, useState } from "react";
import { clearTokens, getAccessToken, getMe, login } from "./api";
import Dashboard from "./Dashboard";

type User = { id: number; username: string; email: string; is_staff: boolean };
export type Theme = "light" | "dark";

function getInitialTheme(): Theme {
  const saved = localStorage.getItem("theme");
  if (saved === "light" || saved === "dark") {
    return saved;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(getAccessToken()));
  const [error, setError] = useState("");
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!getAccessToken()) {
      setLoading(false);
      return;
    }

    getMe()
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  function toggleTheme() {
    setTheme((current) => (current === "light" ? "dark" : "light"));
  }

  if (loading) {
    return <div className="center-screen">Загрузка системы…</div>;
  }

  if (user) {
    return (
      <Dashboard
        user={user}
        theme={theme}
        onToggleTheme={toggleTheme}
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

    try {
      await login(username, password);
      setUser(await getMe());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось выполнить вход.");
    }
  }

  return (
    <main className="auth-page">
      <button
        type="button"
        className="theme-toggle auth-theme-toggle"
        onClick={toggleTheme}
        aria-label={
          theme === "light"
            ? "Переключить на тёмную тему"
            : "Переключить на светлую тему"
        }
      >
        <span aria-hidden="true">{theme === "light" ? "☾" : "☀"}</span>
        {theme === "light" ? "Тёмная тема" : "Светлая тема"}
      </button>

      <section className="auth-hero">
        <h1>
          Разработка геоинформационной системы оценки обеспеченности
          урбанизированной территории объектами социальной инфраструктуры
        </h1>
        <p>
          Анализ доступности объектов социальной инфраструктуры и соответствия
          установленным нормативам.
        </p>
      </section>

      <form className="auth-card" onSubmit={submit}>
        <h2>Вход в систему</h2>

        <label>
          Логин
          <input
            name="username"
            defaultValue="pavel"
            required
            autoComplete="username"
          />
        </label>

        <label>
          Пароль
          <input
            name="password"
            type="password"
            minLength={8}
            required
            autoComplete="current-password"
          />
        </label>

        {error && <div className="error">{error}</div>}

        <button type="submit">Войти</button>
      </form>
    </main>
  );
}
