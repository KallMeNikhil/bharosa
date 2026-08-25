import type { ParticipantView } from "../api/types";

export function SupplyChainFlow({
  participants,
  territoryCount,
}: {
  participants: ParticipantView[];
  territoryCount: number;
}) {
  const countOf = (role: string) => participants.filter((row) => row.role === role).length;

  const nodes = [
    { label: "Manufacturer", count: 1, fixed: true },
    { label: "Depot", count: countOf("DEPOT") },
    { label: "Distributor", count: countOf("DISTRIBUTOR") },
    { label: "Retailer", count: countOf("RETAILER") },
  ];

  return (
    <div className="ink-surface supply-flow">
      {nodes.map((node, index) => (
        <span key={node.label} className="supply-flow__segment">
          {index > 0 && <span className="supply-flow__link" />}
          <span className="supply-flow__node">
            <span className="supply-flow__count">{node.fixed ? "—" : node.count}</span>
            <span className="supply-flow__label">{node.label}</span>
          </span>
        </span>
      ))}
      <span className="supply-flow__aside muted">
        {territoryCount} authorized territor{territoryCount === 1 ? "y" : "ies"} declared
      </span>
    </div>
  );
}
