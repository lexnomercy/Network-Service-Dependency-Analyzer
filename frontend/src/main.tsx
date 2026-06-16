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
type ServiceName = "Zoom API" | "Meetings" | "Media UDP" | "Chat";
type LoadState = "loading" | "ready" | "failed";

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

const serviceNames: ServiceName[] = ["Zoom API", "Meetings", "Media UDP", "Chat"];

const matrixRows = [
  {
    location: "Office MSK",
    services: {
      "Zoom API": "info",
      Meetings: "critical",
      "Media UDP": "warning",
      Chat: "warning",
    },
  },
  {
    location: "Office SPB",
    services: {
      "Zoom API": "info",
      Meetings: "info",
      "Media UDP": "warning",
      Chat: "info",
    },
  },
  {
    location: "Cloud EU",
    services: {
      "Zoom API": "info",
      Meetings: "info",
      "Media UDP": "info",
      Chat: "info",
    },
  },
] satisfies Array<{ location: string; services: Record<ServiceName, Severity> }>;

const chainSteps = [
  { name: "Agent", severity: "info", detail: "office-msk-01 online" },
  { name: "LAN", severity: "info", detail: "gateway reachable" },
  { name: "DNS", severity: "info", detail: "zoom.us resolved" },
  { name: "Firewall/NAT", severity: "critical", detail: "TCP/443 timeout" },
  { name: "Internet Route", severity: "unknown", detail: "blocked by firewall_nat" },
  { name: "Zoom Edge", severity: "unknown", detail: "not reached" },
  { name: "Core Service", severity: "unknown", detail: "not confirmed" },
  { name: "Dependent Service", severity: "unknown", detail: "meeting signaling affected" },
  { name: "Journey", severity: "critical", detail: "Join Meeting failed" },
] satisfies Array<{ name: string; severity: Severity; detail: string }>;

const evidence = [
  "DNS succeeded from affected agents",
  "TCP/443 timed out from Office MSK",
  "Cloud EU agent reached the same endpoint",
  "TLS and HTTP checks were skipped because TCP did not succeed",
];

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

  const criticalResult = findCriticalResult(overview);
  const conclusion = overview?.diagnostic_conclusions[0] ?? null;
  const displayedChain = buildDisplayedChain(criticalResult);
  const displayedEvidence = conclusion?.evidence.map((item) => item.message) ?? evidence;
const displayedActions = conclusion?.recommended_actions.length
    ? conclusion.recommended_actions
    : [
        "Проверьте outbound TCP/443 policy для Zoom endpoints.",
        "Проверьте proxy authentication и bypass rules.",
        "Сопоставьте firewall logs со временем failed check.",
        "Запустите тот же check с другого agent в Office MSK.",
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
          label="Сервисы"
          value={`${overview?.services_total ?? 4} под наблюдением`}
          severity="info"
        />
        <StatusTile
          icon={<MapPinned />}
          label="Агенты"
          value={`${overview?.agents_total ?? 0} зарегистрировано`}
          severity={overview?.agents_total ? "info" : "unknown"}
        />
        <StatusTile
          icon={<GitBranch />}
          label="Результаты"
          value={`${overview?.latest_results.length ?? displayedChain.length} последних`}
          severity={criticalResult ? "warning" : "info"}
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
          <PanelTitle icon={<Signal />} title="Матрица статусов" />
          <StatusMatrix rows={matrixData} />
        </section>

        <section className="panel" aria-label="Диагностический вывод">
          <PanelTitle icon={<ShieldAlert />} title="Диагностический вывод" />
          <div className="conclusion">
            <div>
              <p className="label">Вероятная причина</p>
              <strong>{conclusion?.root_cause ?? "Corporate firewall"}</strong>
            </div>
            <div>
              <p className="label">Уверенность</p>
              <strong>{formatConfidence(conclusion)}</strong>
            </div>
            <div>
              <p className="label">Влияние</p>
              <strong>{titleCase(conclusion?.business_impact ?? "high")}</strong>
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
                <small>{step.detail}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="panel" aria-label="Доказательства">
          <PanelTitle icon={<CheckCircle2 />} title="Доказательства" />
          <ul className="evidence-list">
            {displayedEvidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="panel" aria-label="Рекомендуемые действия">
          <PanelTitle icon={<TimerReset />} title="Рекомендуемые действия" />
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

function StatusMatrix({ rows }: { rows: Array<{ location: string; services: Record<ServiceName, Severity> }> }) {
  return (
    <div className="matrix-wrap">
      <table className="matrix">
        <thead>
          <tr>
            <th>Локация</th>
            {serviceNames.map((service) => (
              <th key={service}>{service}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.location}>
              <th>{row.location}</th>
              {serviceNames.map((service) => (
                <td key={service}>
                  <span className={`status-dot status-dot--${row.services[service]}`} />
                  {labelFor(row.services[service])}
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
    unknown: "Unknown",
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

function buildDisplayedChain(result: CheckResult | null) {
  if (!result || result.chain.length === 0) {
    return chainSteps;
  }

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
  const resultByStep = new Map(result.chain.map((step) => [step.step, step]));
  const failedIndex = baseSteps.findIndex((step) => {
    const chainStep = resultByStep.get(step);
    return chainStep?.severity === "critical" || chainStep?.status === "failed" || chainStep?.status === "timeout";
  });

  return baseSteps.map((step, index) => {
    const chainStep = resultByStep.get(step);
    if (chainStep) {
      return {
        name: chainLabel(step),
        severity: chainStep.severity,
        detail: chainStepDetail(chainStep, result),
      };
    }

  if (failedIndex >= 0 && index > failedIndex) {
      return {
        name: chainLabel(step),
        severity: "unknown" as Severity,
        detail: `blocked after ${chainLabel(baseSteps[failedIndex])}`,
      };
    }

    if (index < 2) {
      return {
        name: chainLabel(step),
        severity: "info" as Severity,
        detail: "assumed reachable",
      };
    }

    return {
      name: chainLabel(step),
      severity: "unknown" as Severity,
      detail: "not observed",
    };
  });
}

function buildMatrixRows(overview: StatusOverview | null) {
  if (!overview || overview.latest_results.length === 0) {
    return matrixRows;
  }

  const rows = new Map<string, Record<ServiceName, Severity>>();
  for (const result of overview.latest_results) {
    const location = result.location_id || "unknown";
    const current =
      rows.get(location) ??
      ({
        "Zoom API": "unknown",
        Meetings: "unknown",
        "Media UDP": "unknown",
        Chat: "unknown",
      } satisfies Record<ServiceName, Severity>);
    const service = serviceNameFor(result.service_id);
    current[service] = worstSeverity(current[service], result.severity);
    rows.set(location, current);
  }

  return Array.from(rows.entries()).map(([location, services]) => ({ location, services }));
}

function chainStepDetail(step: ChainStepResult, result: CheckResult) {
  const address = step.node_address ?? endpointAddress(result);
  const description = step.description ?? step.error_type ?? step.status;
  return address ? `Узел: ${address}. ${description}` : description;
}

function endpointAddress(result: CheckResult) {
  if (!result.endpoint_host) {
    return null;
  }
  return result.endpoint_port ? `${result.endpoint_host}:${result.endpoint_port}` : result.endpoint_host;
}

function serviceNameFor(serviceId: string): ServiceName {
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
  const rank: Record<Severity, number> = {
    info: 0,
    unknown: 1,
    warning: 2,
    critical: 3,
  };
  return rank[next] > rank[current] ? next : current;
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
    return "Live status overview недоступен. Показаны fallback diagnostic data.";
  }
  if (!overview || !result || !conclusion) {
    return "Live incidents пока нет. Показаны fallback diagnostic data до отправки check results от agent.";
  }

  const failedStep = conclusion.failed_step ? chainLabel(conclusion.failed_step) : "unknown step";
  const location = conclusion.affected_locations[0] ?? result.location_id;
  return `${titleCase(spacesForUnderscores(result.service_id))} затронут из локации ${location}. Failed step: ${failedStep}; текущий diagnostic conclusion: ${conclusion.root_cause}.`;
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
