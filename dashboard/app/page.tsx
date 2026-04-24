import Link from "next/link";
import { Activity, CheckCircle2, DollarSign, PhoneCall, Repeat } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { KpiCard } from "@/components/kpi-card";
import {
  CallsOverTimeChart,
  OutcomeBarChart,
  SentimentBarChart,
} from "@/components/charts";
import { CsvExportButton } from "@/components/csv-export-button";
import { getCalls, getMetricsSummary, getPostedRatesFor } from "@/lib/api";
import { formatCurrency, formatPercent, formatRelativeTime } from "@/lib/utils";

export const dynamic = "force-dynamic";

const OUTCOME_BADGE: Record<string, "success" | "warning" | "destructive" | "muted" | "secondary"> = {
  accepted: "success",
  declined: "destructive",
  no_match: "warning",
  ineligible: "muted",
  carrier_dropped: "secondary",
};

const SENTIMENT_BADGE: Record<string, "success" | "destructive" | "muted"> = {
  positive: "success",
  negative: "destructive",
  neutral: "muted",
};

export default async function DashboardPage() {
  const [metrics, callsList] = await Promise.all([
    getMetricsSummary(),
    getCalls(25, 0),
  ]);

  // Look up each call's posted rate (from the Load) so we can show "Listed" vs "Booked"
  const postedRates = await getPostedRatesFor(callsList.calls.map((c) => c.load_id));

  const tableRows = callsList.calls.map((c) => ({
    ...c,
    posted_rate: c.load_id ? postedRates[c.load_id] ?? null : null,
  }));

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 space-y-8">
      {/* Header */}
      <header className="flex flex-col gap-1 border-b pb-6">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          <h1 className="text-xl font-semibold tracking-tight">
            HappyRobot Carrier Sales
          </h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Inbound carrier call performance, sentiment, and negotiation outcomes
        </p>
      </header>

      {/* KPI row */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total Calls"
          value={metrics.calls_total}
          hint={`${metrics.calls_today} today`}
          icon={PhoneCall}
        />
        <KpiCard
          label="Acceptance Rate"
          value={formatPercent(metrics.acceptance_rate)}
          hint="Agreements / total calls"
          icon={CheckCircle2}
        />
        <KpiCard
          label="Avg Rounds to Close"
          value={
            metrics.avg_rounds_when_accepted === null
              ? "—"
              : metrics.avg_rounds_when_accepted.toFixed(2)
          }
          hint="Across accepted calls"
          icon={Repeat}
        />
        <KpiCard
          label="Avg Booked Rate"
          value={formatCurrency(metrics.avg_final_rate)}
          hint="Across accepted calls"
          icon={DollarSign}
        />
      </section>

      {/* Breakdown row */}
      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Outcome Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <OutcomeBarChart data={metrics.outcomes} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Carrier Sentiment</CardTitle>
          </CardHeader>
          <CardContent>
            <SentimentBarChart data={metrics.sentiment} />
          </CardContent>
        </Card>
      </section>

      {/* Trend */}
      <section>
        <Card>
          <CardHeader>
            <CardTitle>Calls — last 14 days</CardTitle>
          </CardHeader>
          <CardContent>
            <CallsOverTimeChart data={metrics.calls_by_day} />
          </CardContent>
        </Card>
      </section>

      {/* Recent calls table */}
      <section>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>Recent Calls</CardTitle>
            <CsvExportButton rows={tableRows} />
          </CardHeader>
          <CardContent className="px-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Carrier</TableHead>
                  <TableHead>MC</TableHead>
                  <TableHead>Load</TableHead>
                  <TableHead>Outcome</TableHead>
                  <TableHead>Sentiment</TableHead>
                  <TableHead className="text-right">Rounds</TableHead>
                  <TableHead className="text-right">Listed</TableHead>
                  <TableHead className="text-right">Booked</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tableRows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                      No calls logged yet
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRows.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="text-muted-foreground text-xs">
                        {formatRelativeTime(c.created_at)}
                      </TableCell>
                      <TableCell className="font-medium">
                        <Link href={`/calls/${c.id}`} className="hover:underline">
                          {c.carrier_name ?? "—"}
                        </Link>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{c.mc_number ?? "—"}</TableCell>
                      <TableCell className="font-mono text-xs">{c.load_id ?? "—"}</TableCell>
                      <TableCell>
                        {c.outcome ? (
                          <Badge variant={OUTCOME_BADGE[c.outcome] ?? "secondary"}>
                            {c.outcome}
                          </Badge>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell>
                        {c.sentiment ? (
                          <Badge variant={SENTIMENT_BADGE[c.sentiment] ?? "muted"}>
                            {c.sentiment}
                          </Badge>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell className="text-right">{c.rounds_used ?? "—"}</TableCell>
                      <TableCell className="text-right text-muted-foreground">
                        {formatCurrency(c.posted_rate)}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(c.final_rate)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
