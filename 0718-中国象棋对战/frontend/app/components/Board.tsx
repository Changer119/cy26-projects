import type { ReactNode } from "react";
import { BOARD_COLS, BOARD_ROWS, Board as BoardModel, Position, samePosition } from "@/lib/xiangqi/types";
import { Piece } from "./Piece";

const CELL = 60;
const MARGIN = 40;
const PIECE_SIZE = 50;

const WIDTH = MARGIN * 2 + (BOARD_COLS - 1) * CELL;
const HEIGHT = MARGIN * 2 + (BOARD_ROWS - 1) * CELL;

function toX(col: number) {
  return MARGIN + col * CELL;
}
function toY(row: number) {
  return MARGIN + row * CELL;
}

function GridLines() {
  const lines: ReactNode[] = [];

  for (let row = 0; row < BOARD_ROWS; row++) {
    lines.push(
      <line
        key={`h-${row}`}
        x1={toX(0)}
        y1={toY(row)}
        x2={toX(BOARD_COLS - 1)}
        y2={toY(row)}
        stroke="#5b4636"
        strokeWidth={1.5}
      />,
    );
  }

  for (let col = 0; col < BOARD_COLS; col++) {
    if (col === 0 || col === BOARD_COLS - 1) {
      lines.push(
        <line key={`v-${col}`} x1={toX(col)} y1={toY(0)} x2={toX(col)} y2={toY(BOARD_ROWS - 1)} stroke="#5b4636" strokeWidth={1.5} />,
      );
    } else {
      lines.push(
        <line key={`v-${col}-top`} x1={toX(col)} y1={toY(0)} x2={toX(col)} y2={toY(4)} stroke="#5b4636" strokeWidth={1.5} />,
      );
      lines.push(
        <line key={`v-${col}-bottom`} x1={toX(col)} y1={toY(5)} x2={toX(col)} y2={toY(BOARD_ROWS - 1)} stroke="#5b4636" strokeWidth={1.5} />,
      );
    }
  }

  const palaceDiagonals = [
    [0, 3, 2, 5],
    [0, 5, 2, 3],
    [7, 3, 9, 5],
    [7, 5, 9, 3],
  ];
  palaceDiagonals.forEach(([r1, c1, r2, c2], idx) => {
    lines.push(
      <line key={`palace-${idx}`} x1={toX(c1)} y1={toY(r1)} x2={toX(c2)} y2={toY(r2)} stroke="#5b4636" strokeWidth={1.5} />,
    );
  });

  return <>{lines}</>;
}

interface BoardProps {
  board: BoardModel;
  selected: Position | null;
  legalTargets: Position[];
  onSelect: (pos: Position) => void;
}

export function XiangqiBoard({ board, selected, legalTargets, onSelect }: BoardProps) {
  return (
    <svg width={WIDTH} height={HEIGHT} className="rounded-lg bg-[#f3d9a5] shadow-lg">
      <GridLines />
      <text x={WIDTH / 2 - CELL * 1.5} y={toY(4.5) + 6} textAnchor="middle" fontSize={22} fill="#5b4636">
        楚 河
      </text>
      <text x={WIDTH / 2 + CELL * 1.5} y={toY(4.5) + 6} textAnchor="middle" fontSize={22} fill="#5b4636">
        汉 界
      </text>

      {legalTargets.map((pos) => (
        <circle
          key={`target-${pos.row}-${pos.col}`}
          cx={toX(pos.col)}
          cy={toY(pos.row)}
          r={board[pos.row][pos.col] ? PIECE_SIZE / 2 + 3 : 7}
          fill={board[pos.row][pos.col] ? "none" : "#3b82f6"}
          stroke="#3b82f6"
          strokeWidth={3}
          opacity={0.7}
        />
      ))}

      {board.map((rowPieces, row) =>
        rowPieces.map((piece, col) =>
          piece ? (
            <Piece
              key={`piece-${row}-${col}`}
              piece={piece}
              x={toX(col)}
              y={toY(row)}
              size={PIECE_SIZE}
              selected={selected !== null && samePosition(selected, { row, col })}
            />
          ) : null,
        ),
      )}

      {board.map((rowPieces, row) =>
        rowPieces.map((_, col) => (
          <rect
            key={`hit-${row}-${col}`}
            data-row={row}
            data-col={col}
            x={toX(col) - CELL / 2}
            y={toY(row) - CELL / 2}
            width={CELL}
            height={CELL}
            fill="transparent"
            onClick={() => onSelect({ row, col })}
            className="cursor-pointer"
          />
        )),
      )}
    </svg>
  );
}
