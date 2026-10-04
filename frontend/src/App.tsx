import { FormEvent, useEffect, useState } from "react";
import { clearTokens, getAccessToken, getMe, login } from "./api";
import Dashboard from "./Dashboard";

type User = { id: number; username: string; email: string; is_staff: boolean };

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(getAccessToken()));
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getAccessToken()) return;

    getMe()
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="center-screen">Загрузка системы…</div>;
  }

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

    try {
      await login(username, password);
      setUser(await getMe());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось выполнить вход");
    }
  }

  return (
    <main className="auth-page">
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
            defaultValue="Павел"
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
