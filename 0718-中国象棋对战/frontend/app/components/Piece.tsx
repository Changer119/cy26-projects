import { Piece as PieceModel } from "@/lib/xiangqi/types";

const LABELS: Record<PieceModel["side"], Record<PieceModel["type"], string>> = {
  red: {
    general: "帅",
    advisor: "仕",
    elephant: "相",
    horse: "马",
    chariot: "车",
    cannon: "炮",
    soldier: "兵",
  },
  black: {
    general: "将",
    advisor: "士",
    elephant: "象",
    horse: "马",
    chariot: "车",
    cannon: "炮",
    soldier: "卒",
  },
};

interface PieceProps {
  piece: PieceModel;
  x: number;
  y: number;
  size: number;
  selected: boolean;
}

export function Piece({ piece, x, y, size, selected }: PieceProps) {
  const radius = size / 2;
  const isRed = piece.side === "red";

  return (
    <g transform={`translate(${x}, ${y})`} className="select-none">
      <circle
        r={radius}
        fill={isRed ? "#fdf1e0" : "#2b2b2b"}
        stroke={selected ? "#3b82f6" : isRed ? "#b91c1c" : "#d4d4d8"}
        strokeWidth={selected ? 4 : 2}
      />
      <circle r={radius - 4} fill="none" stroke={isRed ? "#b91c1c" : "#9ca3af"} strokeWidth={1} />
      <text
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={radius}
        fontWeight={700}
        fill={isRed ? "#b91c1c" : "#e5e7eb"}
      >
        {LABELS[piece.side][piece.type]}
      </text>
    </g>
  );
}
