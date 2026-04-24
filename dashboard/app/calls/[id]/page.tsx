import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
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
import { getCallDetail, getPostedRatesFor } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export const dynamic = "force-dynamic";

const DECISION_BADGE: Record<string, "success" | "warning" | "destructive" | "muted"> = {
  accept: "success",
  counter: "warning",
  decline: "destructive",
  pending: "muted",
};

export default async function CallDetailPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  if (!Number.isFinite(id)) notFound();

  let detail;
  try {
    detail = await getCallDetail(id);
  } catch {
    notFound();
  }

  const { call, offers, transcript } = detail;
  const postedRates = await getPostedRatesFor([call.load_id]);
  const postedRate = call.load_id ? postedRates[call.load_id] ?? null : null;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 space-y-8">
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
        <h1 className="text-xl font-semibold tracking-tight">
          {call.carrier_name ?? "Unknown carrier"}
          <span className="text-muted-foreground"> — call #{call.id}</span>
        </h1>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>MC Number</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-mono">{call.mc_number ?? "—"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Load</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-mono">{call.load_id ?? "—"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Outcome</CardTitle>
          </CardHeader>
          <CardContent>
            {call.outcome ? <Badge>{call.outcome}</Badge> : "—"}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Listed → Booked</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-sm text-muted-foreground line-through">
                {formatCurrency(postedRate)}
              </span>
              <span className="text-xl font-semibold">
                {formatCurrency(call.final_rate)}
              </span>
            </div>
          </CardContent>
        </Card>
      </section>

      <section>
        <Card>
          <CardHeader>
            <CardTitle>Negotiation Rounds</CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Round</TableHead>
                  <TableHead className="text-right">Carrier Offer</TableHead>
                  <TableHead className="text-right">Agent Counter</TableHead>
                  <TableHead>Decision</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {offers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-6">
                      No offers recorded
                    </TableCell>
                  </TableRow>
                ) : (
                  offers.map((o) => (
                    <TableRow key={o.id}>
                      <TableCell>{o.round_number}</TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(o.carrier_offer)}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {o.decision === "counter"
                          ? formatCurrency(o.agent_counter)
                          : <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell>
                        <Badge variant={DECISION_BADGE[o.decision] ?? "secondary"}>
                          {o.decision === "accept" && o.agent_counter
                            ? `accepted @ ${formatCurrency(o.agent_counter)}`
                            : o.decision}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </section>

      {transcript && (
        <section>
          <Card>
            <CardHeader>
              <CardTitle>Transcript</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap text-xs leading-relaxed font-mono text-muted-foreground">
                {transcript}
              </pre>
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  );
}
