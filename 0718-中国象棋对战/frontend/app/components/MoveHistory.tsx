import { MoveRecord } from "@/lib/xiangqi/types";

const PIECE_NAMES: Record<string, string> = {
  general: "将",
  advisor: "士",
  elephant: "象",
  horse: "马",
  chariot: "车",
  cannon: "炮",
  soldier: "卒",
};

function formatMove(record: MoveRecord, index: number): string {
  const side = record.piece.side === "red" ? "红" : "黑";
  const name = PIECE_NAMES[record.piece.type];
  const from = `${record.move.from.row},${record.move.from.col}`;
  const to = `${record.move.to.row},${record.move.to.col}`;
  const captureMark = record.captured ? "吃子" : "";
  return `${index + 1}. ${side}${name} (${from}) → (${to}) ${captureMark}`;
}

interface MoveHistoryProps {
  history: MoveRecord[];
}

export function MoveHistory({ history }: MoveHistoryProps) {
  return (
    <div className="flex h-[560px] w-64 flex-col rounded-lg bg-white/80 p-3 shadow">
      <h2 className="mb-2 text-sm font-semibold text-neutral-700">走子记录</h2>
      <div className="flex-1 overflow-y-auto text-xs leading-6 text-neutral-600">
        {history.length === 0 && <p className="text-neutral-400">暂无走子</p>}
        {history.map((record, index) => (
          <div key={index}>{formatMove(record, index)}</div>
        ))}
      </div>
    </div>
  );
}
