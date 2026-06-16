import React from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  GitBranch,
  MapPinned,
  ShieldAlert,
  Signal,
  TimerReset,
} from "lucide-react";
import "./styles.css";

type HealthState = "loading" | "ok" | "failed";
type Severity = "info" | "warning" | "critical" | "unknown";
type LoadState = "loading" | "ready" | "failed";
type MonitoringState = "app_problem" | "no_data" | "healthy" | "degraded" | "critical";
type MatrixCell = {
  severity: Severity;
  checks: number;
  endpoint: string;
};
type MatrixRow = {
  location: string;
  services: Record<string, MatrixCell>;
};

type ChainStepResult = {
  step: string;
  status: string;
  severity: Severity;
  node_address: string | null;
  description: string | null;
  error_type: string | null;
};

type Evidence = {
  type: string;
  message: string;
  source: string;
  weight: number;
};

type CheckResult = {
  agent_id: string;
  location_id: string;
  service_id: string;
  endpoint_group_id: string | null;
  endpoint_host: string | null;
  endpoint_port: number | null;
  endpoint_path: string | null;
  check_type: string;
  status: string;
  severity: Severity;
  duration_ms: number | null;
  error_type: string | null;
  technical_description: string | null;
  probable_cause: string | null;
  recommended_actions: string[];
  chain: ChainStepResult[];
  evidence: Evidence[];
};

type Incident = {
  id: string;
  title: string;
  service_id: string;
  location_id: string;
  severity: Severity;
  root_step: string | null;
  error_type: string | null;
  summary: string | null;
};

type DiagnosticConclusion = {
  root_cause: string;
  root_cause_confidence: number;
  confidence_level: string;
  failed_step: string | null;
  affected_services: string[];
  affected_locations: string[];
  business_impact: string;
  evidence: Evidence[];
  recommended_actions: string[];
};

type StatusOverview = {
  services_total: number;
  agents_total: number;
  open_incidents: number;
  latest_results: CheckResult[];
  incidents: Incident[];
  diagnostic_conclusions: DiagnosticConclusion[];
};

function App() {
  const [health, setHealth] = React.useState<HealthState>("loading");
  const [overview, setOverview] = React.useState<StatusOverview | null>(null);
  const [overviewState, setOverviewState] = React.useState<LoadState>("loading");

  React.useEffect(() => {
    fetch("/health")
      .then((response) => {
        setHealth(response.ok ? "ok" : "failed");
      })
      .catch(() => setHealth("failed"));
  }, []);

  React.useEffect(() => {
    fetch("/api/v1/status/overview")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`status overview failed: ${response.status}`);
        }
        return response.json() as Promise<StatusOverview>;
      })
      .then((data) => {
        setOverview(data);
        setOverviewState("ready");
      })
      .catch(() => {
        setOverviewState("failed");
      });
  }, []);

  const endpointResults = selectEndpointResults(overview);
  const criticalResult = findCriticalResult(overview);
  const conclusion = overview?.diagnostic_conclusions[0] ?? null;
  const monitoringState = getMonitoringState(health, overviewState, overview);
  const displayedChain = buildDisplayedChain(endpointResults, overview);
  const displayedEvidence = buildEvidenceFacts(health, overviewState, overview, endpointResults, conclusion);
  const displayedActions = conclusion?.recommended_actions.length
    ? conclusion.recommended_actions
    : [
        "Если нужно обновить данные, запустите: .venv/bin/python -m agent.main run-service-pack --pack zoom --submit",
        "Если видите 'нет данных', проверьте что backend запущен и агент отправил результаты.",
        "Если есть Critical, откройте проблемный узел в цепочке и проверьте его node_address.",
      ];
  const matrixData = buildMatrixRows(overview);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Network Service Dependency Analyzer</p>
          <h1>Dashboard зависимостей Zoom-сервисов</h1>
        </div>
        <div className={`backend-pill backend-pill--${health}`}>
          <Activity size={16} />
          <span>Backend: {health}</span>
        </div>
      </header>

      <section className="status-grid" aria-label="Сводка статусов">
        <StatusTile
          icon={<Activity />}
          label="Состояние приложения"
          value={health === "ok" ? "Backend отвечает" : "Backend недоступен"}
          severity={health === "ok" ? "info" : "critical"}
        />
        <StatusTile
          icon={<MapPinned />}
          label="Данные мониторинга"
          value={overview?.latest_results.length ? `${overview.latest_results.length} checks получено` : "Нет check results"}
          severity={overview?.latest_results.length ? "info" : "unknown"}
        />
        <StatusTile
          icon={<GitBranch />}
          label="Проверенный endpoint"
          value={endpointLabel(endpointResults)}
          severity={endpointResults.length ? "info" : "unknown"}
        />
        <StatusTile
          icon={<AlertTriangle />}
          label="Инциденты"
          value={`${overview?.open_incidents ?? 1} открыто`}
          severity={overview?.open_incidents ? "critical" : "info"}
        />
      </section>

      <div className="dashboard-layout">
        <section className="panel" aria-label="Матрица статусов">
          <PanelTitle icon={<Signal />} title="Сводка по сервисам и локациям" />
          <p className="panel-note">
            Это не отдельная проверка. Здесь агрегируются последние check results: строка - локация,
            колонка - сервис/endpoint group, ячейка - худший статус проверок DNS/TCP/TLS/HTTP.
          </p>
          <StatusMatrix rows={matrixData} />
        </section>

        <section className="panel" aria-label="Диагностический вывод">
          <PanelTitle icon={<ShieldAlert />} title="Что происходит" />
          <div className={`state-banner state-banner--${monitoringState}`}>
            <strong>{stateTitle(monitoringState)}</strong>
            <span>{stateDescription(monitoringState, overview, endpointResults)}</span>
          </div>
          <div className="conclusion">
            <div>
              <p className="label">Источник проблемы</p>
              <strong>{conclusion?.root_cause ?? sourceLabel(monitoringState)}</strong>
            </div>
            <div>
              <p className="label">Уверенность</p>
              <strong>{conclusion ? formatConfidence(conclusion) : confidenceLabel(monitoringState)}</strong>
            </div>
            <div>
              <p className="label">Влияние</p>
              <strong>{conclusion ? titleCase(conclusion.business_impact) : impactLabel(monitoringState)}</strong>
            </div>
          </div>
          <p className="summary">
            {buildSummary(overviewState, overview, criticalResult, conclusion)}
          </p>
        </section>

        <section className="panel panel--wide" aria-label="Цепочка соединения">
          <PanelTitle icon={<GitBranch />} title="Цепочка соединения" />
          <div className="chain">
            {displayedChain.map((step) => (
              <div className={`chain-step chain-step--${step.severity}`} key={step.name}>
                <span className="dot" />
                <span className="step-name">{step.name}</span>
                <small className="step-address">Адрес: {step.address}</small>
                <small>{step.detail}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="panel" aria-label="Факты проверки">
          <PanelTitle icon={<CheckCircle2 />} title="Факты проверки" />
          <ul className="evidence-list">
            {displayedEvidence.map((item) => (
              <li key={`${item.fact}-${item.proves}`}>
                <strong>{item.fact}</strong>
                <span>{item.proves}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel" aria-label="Что делать дальше">
          <PanelTitle icon={<TimerReset />} title="Что делать дальше" />
          <ol className="action-list">
            {displayedActions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ol>
        </section>
      </div>
    </main>
  );
}

function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="panel-title">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

function StatusMatrix({ rows }: { rows: MatrixRow[] }) {
  const columns = matrixColumns(rows);

  if (columns.length === 0) {
    return (
      <div className="empty-state">
        <strong>Данных мониторинга пока нет</strong>
        <span>Запустите агент: .venv/bin/python -m agent.main run-service-pack --pack zoom --submit</span>
      </div>
    );
  }

  return (
    <div className="matrix-wrap">
      <table className="matrix">
        <thead>
          <tr>
            <th>Локация</th>
            {columns.map((service) => (
              <th key={service}>{service}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.location}>
              <th>{row.location}</th>
              {columns.map((service) => (
                <td key={service}>
                  {row.services[service] ? (
                    <div className="matrix-cell">
                      <span>
                        <span className={`status-dot status-dot--${row.services[service].severity}`} />
                        {labelFor(row.services[service].severity)}
                      </span>
                      <small>{row.services[service].endpoint}</small>
                      <small>{row.services[service].checks} checks</small>
                    </div>
                  ) : (
                    <span className="muted">не проверялось</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusTile({
  icon,
  label,
  value,
  severity
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  severity: Severity;
}) {
  return (
    <article className={`status-tile status-tile--${severity}`}>
      <div className="tile-icon">{icon}</div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

function labelFor(severity: Severity) {
  return {
    info: "OK",
    warning: "Warn",
    critical: "Critical",
    unknown: "Нет данных",
  }[severity];
}

function findCriticalResult(overview: StatusOverview | null): CheckResult | null {
  if (!overview) {
    return null;
  }
  return (
    overview.latest_results.find((result) => result.severity === "critical") ??
    overview.latest_results.find((result) => result.severity === "warning") ??
    overview.latest_results[0] ??
    null
  );
}

function selectEndpointResults(overview: StatusOverview | null): CheckResult[] {
  if (!overview?.latest_results.length) {
    return [];
  }

  const groups = new Map<string, CheckResult[]>();
  for (const result of overview.latest_results) {
    const key = [
      result.location_id,
      result.service_id,
      result.endpoint_group_id ?? "",
      result.endpoint_host ?? "",
      result.endpoint_port ?? "",
      result.endpoint_path ?? "",
    ].join("|");
    const current = groups.get(key) ?? [];
    current.push(result);
    groups.set(key, current);
  }

  const allGroups = Array.from(groups.values());
  return (
    allGroups.find((group) => group.some((result) => result.severity === "critical")) ??
    allGroups.find((group) => group.some((result) => result.severity === "warning")) ??
    allGroups[0] ??
    []
  );
}

function buildDisplayedChain(results: CheckResult[], overview: StatusOverview | null) {
  const baseSteps = [
    "local_agent",
    "lan",
    "dns",
    "proxy_firewall_nat",
    "internet_route",
    "service_edge",
    "core_service",
    "dependent_service",
    "application_service",
  ];

  if (results.length === 0) {
    return baseSteps.map((step) => ({
      name: chainLabel(step),
      severity: step === "local_agent" && overview ? ("info" as Severity) : ("unknown" as Severity),
      address: "нет данных",
      detail: step === "local_agent" && overview ? "Backend работает, но агент еще не отправил checks" : "узел не проверялся",
    }));
  }

  const representative = results[0];
  const stepCandidates = new Map<string, Array<{ step: ChainStepResult; result: CheckResult }>>();

  for (const result of results) {
    for (const step of result.chain) {
      const current = stepCandidates.get(step.step) ?? [];
      current.push({ step, result });
      stepCandidates.set(step.step, current);
    }
  }

  const failedIndex = baseSteps.findIndex((step) => {
    const chainStep = worstStep(stepCandidates.get(step));
    return chainStep?.severity === "critical" || chainStep?.status === "failed" || chainStep?.status === "timeout";
  });

  return baseSteps.map((step, index) => {
    if (step === "local_agent") {
      return {
        name: chainLabel(step),
        severity: "info" as Severity,
        address: representative.agent_id,
        detail: `Локация: ${representative.location_id}`,
      };
    }

    if (step === "lan") {
      return {
        name: chainLabel(step),
        severity: "unknown" as Severity,
        address: "локальная сеть агента",
        detail: "MVP не выполняет отдельную LAN-проверку",
      };
    }

    const candidate = worstStepWithResult(stepCandidates.get(step));
    if (candidate) {
      return {
        name: chainLabel(step),
        severity: candidate.step.severity,
        address: candidate.step.node_address ?? endpointAddress(candidate.result) ?? "нет адреса",
        detail: chainStepDescription(candidate.step, candidate.result),
      };
    }

    if (step === "core_service" || step === "dependent_service") {
      return {
        name: chainLabel(step),
        severity: "unknown" as Severity,
        address: endpointAddress(representative) ?? "нет адреса",
        detail: "не проверяется текущим MVP без synthetic journey",
      };
    }

    if (failedIndex >= 0 && index > failedIndex) {
      return {
        name: chainLabel(step),
        severity: "unknown" as Severity,
        address: endpointAddress(representative) ?? "нет адреса",
        detail: `не проверялся, потому что раньше упал узел ${chainLabel(baseSteps[failedIndex])}`,
      };
    }

    return {
      name: chainLabel(step),
      severity: "unknown" as Severity,
      address: endpointAddress(representative) ?? "нет адреса",
      detail: "нет результата для этого этапа",
    };
  });
}

function buildMatrixRows(overview: StatusOverview | null) {
  if (!overview || overview.latest_results.length === 0) {
    return [];
  }

  const rows = new Map<string, MatrixRow>();
  for (const result of overview.latest_results) {
    const location = result.location_id || "unknown";
    const current =
      rows.get(location) ??
      ({
        location,
        services: {},
      } satisfies MatrixRow);
    const service = serviceNameFor(result.service_id);
    const previous = current.services[service];
    current.services[service] = {
      severity: previous ? worstSeverity(previous.severity, result.severity) : result.severity,
      checks: (previous?.checks ?? 0) + 1,
      endpoint: endpointAddress(result) ?? result.endpoint_group_id ?? result.service_id,
    };
    rows.set(location, current);
  }

  return Array.from(rows.values());
}

function matrixColumns(rows: MatrixRow[]) {
  return Array.from(new Set(rows.flatMap((row) => Object.keys(row.services))));
}

function buildEvidenceFacts(
  health: HealthState,
  state: LoadState,
  overview: StatusOverview | null,
  results: CheckResult[],
  conclusion: DiagnosticConclusion | null
) {
  if (health !== "ok") {
    return [
      {
        fact: "Backend не отвечает на /health",
        proves: "Проблема в самом приложении или локальном запуске backend.",
      },
    ];
  }

  if (state === "failed") {
    return [
      {
        fact: "Frontend не смог получить /api/v1/status/overview",
        proves: "Backend может быть запущен, но API недоступен для dashboard.",
      },
    ];
  }

  if (!overview?.latest_results.length) {
    return [
      {
        fact: "Backend отвечает, но check results отсутствуют",
        proves: "Само приложение работает; агент еще не отправил результаты мониторинга.",
      },
    ];
  }

  if (conclusion?.evidence.length) {
    return conclusion.evidence.map((item) => ({
      fact: item.message,
      proves: `Источник: ${item.source}; вес evidence: ${item.weight}.`,
    }));
  }

  const facts = [
    {
      fact: `Backend принял ${overview.latest_results.length} check results`,
      proves: "Приложение работает, API ingestion и status overview доступны.",
    },
  ];

  for (const result of sortChecks(results)) {
    facts.push({
      fact: `${result.check_type.toUpperCase()} ${result.status}: ${endpointAddress(result) ?? "адрес не указан"}`,
      proves: factMeaning(result),
    });
  }

  return facts;
}

function factMeaning(result: CheckResult) {
  if (result.check_type === "dns" && result.status === "success") {
    return "DNS resolver смог получить IP для этого hostname.";
  }
  if (result.check_type === "tcp" && result.status === "success") {
    return "До адреса можно открыть TCP-соединение; путь через firewall/NAT/route не заблокирован для этого порта.";
  }
  if (result.check_type === "tls" && result.status === "success") {
    return "TLS handshake и certificate validation прошли успешно.";
  }
  if (result.check_type === "http" && result.status === "success") {
    return "Прикладной HTTP endpoint ответил, Zoom edge/application layer достижим.";
  }
  if (result.status === "skipped") {
    return "Проверка не выполнялась, потому что предыдущий этап цепочки не прошел.";
  }
  return result.technical_description ?? result.error_type ?? "Есть технический сбой на этом этапе.";
}

function chainStepDescription(step: ChainStepResult, result: CheckResult) {
  return step.description ?? result.technical_description ?? step.error_type ?? step.status;
}

function worstStep(candidates: Array<{ step: ChainStepResult; result: CheckResult }> | undefined) {
  return worstStepWithResult(candidates)?.step;
}

function worstStepWithResult(candidates: Array<{ step: ChainStepResult; result: CheckResult }> | undefined) {
  if (!candidates?.length) {
    return null;
  }
  return [...candidates].sort((left, right) => severityRank(right.step.severity) - severityRank(left.step.severity))[0];
}

function endpointAddress(result: CheckResult) {
  if (!result.endpoint_host) {
    return null;
  }
  return result.endpoint_port ? `${result.endpoint_host}:${result.endpoint_port}` : result.endpoint_host;
}

function serviceNameFor(serviceId: string): string {
  if (serviceId.includes("media")) {
    return "Media UDP";
  }
  if (serviceId.includes("chat")) {
    return "Chat";
  }
  if (serviceId.includes("api") || serviceId.includes("auth")) {
    return "Zoom API";
  }
  return "Meetings";
}

function worstSeverity(current: Severity, next: Severity): Severity {
  return severityRank(next) > severityRank(current) ? next : current;
}

function severityRank(severity: Severity) {
  return {
    info: 0,
    unknown: 1,
    warning: 2,
    critical: 3,
  }[severity];
}

function formatConfidence(conclusion: DiagnosticConclusion | null) {
  if (!conclusion) {
    return "0.94 High";
  }
  return `${conclusion.root_cause_confidence.toFixed(2)} ${titleCase(conclusion.confidence_level)}`;
}

function buildSummary(
  state: LoadState,
  overview: StatusOverview | null,
  result: CheckResult | null,
  conclusion: DiagnosticConclusion | null
) {
  if (state === "loading") {
    return "Загружается live status overview из backend.";
  }
  if (state === "failed") {
    return "Live status overview недоступен. Это проблема связи frontend с backend API.";
  }
  if (!overview || !result || !conclusion) {
    if (overview?.latest_results.length) {
      return "Инцидентов нет. Последние checks успешно приняты backend, смотрите цепочку ниже по выбранному endpoint.";
    }
    return "Инцидентов и check results пока нет. Запустите агент, чтобы увидеть состояние Zoom endpoints.";
  }

  const failedStep = conclusion.failed_step ? chainLabel(conclusion.failed_step) : "unknown step";
  const location = conclusion.affected_locations[0] ?? result.location_id;
  return `${titleCase(spacesForUnderscores(result.service_id))} затронут из локации ${location}. Failed step: ${failedStep}; текущий diagnostic conclusion: ${conclusion.root_cause}.`;
}

function getMonitoringState(
  health: HealthState,
  state: LoadState,
  overview: StatusOverview | null
): MonitoringState {
  if (health === "failed" || state === "failed") {
    return "app_problem";
  }
  if (!overview?.latest_results.length) {
    return "no_data";
  }
  if (overview.open_incidents > 0 || overview.latest_results.some((result) => result.severity === "critical")) {
    return "critical";
  }
  if (overview.latest_results.some((result) => result.severity === "warning")) {
    return "degraded";
  }
  return "healthy";
}

function stateTitle(state: MonitoringState) {
  return {
    app_problem: "Проблема с приложением",
    no_data: "Приложение работает, но данных мониторинга нет",
    healthy: "Zoom endpoints доступны из этой локации",
    degraded: "Есть деградация",
    critical: "Есть критическая проблема доступа",
  }[state];
}

function stateDescription(state: MonitoringState, overview: StatusOverview | null, results: CheckResult[]) {
  const endpoint = endpointLabel(results);
  return {
    app_problem: "Frontend или backend API не отвечают корректно.",
    no_data: "Backend запущен. Нужно запустить агент, чтобы выполнить DNS/TCP/TLS/HTTP checks.",
    healthy: `Проверки прошли успешно. Выбранный endpoint: ${endpoint}.`,
    degraded: `Есть warning на одном из этапов. Выбранный endpoint: ${endpoint}.`,
    critical: `Есть critical на одном из этапов. Адрес проблемного узла показан в цепочке ниже.`,
  }[state];
}

function sourceLabel(state: MonitoringState) {
  return {
    app_problem: "Frontend/backend",
    no_data: "Агент не запускался",
    healthy: "Проблем не обнаружено",
    degraded: "См. warning в цепочке",
    critical: "См. critical узел в цепочке",
  }[state];
}

function confidenceLabel(state: MonitoringState) {
  return state === "healthy" ? "Confirmed by checks" : "Недостаточно данных";
}

function impactLabel(state: MonitoringState) {
  return {
    app_problem: "Dashboard недоступен",
    no_data: "Неизвестно",
    healthy: "Нет влияния",
    degraded: "Среднее",
    critical: "Высокое",
  }[state];
}

function endpointLabel(results: CheckResult[]) {
  const result = results[0];
  if (!result) {
    return "нет данных";
  }
  return `${endpointAddress(result) ?? "адрес не указан"}${result.endpoint_path ?? ""}`;
}

function sortChecks(results: CheckResult[]) {
  const order = ["dns", "tcp", "tls", "http"];
  return [...results].sort((left, right) => order.indexOf(left.check_type) - order.indexOf(right.check_type));
}

function chainLabel(step: string) {
  return {
    local_agent: "Agent",
    lan: "LAN",
    dns: "DNS",
    proxy_firewall_nat: "Firewall/NAT",
    internet_route: "Internet Route",
    service_edge: "Service Edge",
    core_service: "Core Service",
    dependent_service: "Dependent Service",
    application_service: "Application Service",
  }[step] ?? titleCase(spacesForUnderscores(step));
}

function titleCase(value: string) {
  return value
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function spacesForUnderscores(value: string) {
  return value.split("_").join(" ");
}

createRoot(document.getElementById("root")!).render(<App />);
