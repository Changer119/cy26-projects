"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { findBestMove } from "@/lib/xiangqi/ai/search";
import { DIFFICULTY_DEPTH } from "@/lib/xiangqi/ai/difficulty";
import { applyMove, cloneBoard, createInitialBoard, getPiece } from "@/lib/xiangqi/board";
import { generateAllLegalMoves, generateLegalMoves, getGameResult, isInCheck } from "@/lib/xiangqi/rules";
import {
  Board,
  Difficulty,
  GameResult,
  Move,
  MoveRecord,
  Position,
  Side,
  samePosition,
} from "@/lib/xiangqi/types";

const PLAYER_SIDE: Side = "red";
const COMPUTER_SIDE: Side = "black";

export function useXiangqiGame() {
  const [board, setBoard] = useState<Board>(() => createInitialBoard());
  const [turn, setTurn] = useState<Side>("red");
  const [selected, setSelected] = useState<Position | null>(null);
  const [history, setHistory] = useState<MoveRecord[]>([]);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");

  const result: GameResult = useMemo(() => getGameResult(board, turn), [board, turn]);
  const inCheck = useMemo(() => isInCheck(board, turn), [board, turn]);
  const thinking = result === "playing" && turn === COMPUTER_SIDE;

  const legalTargets = useMemo<Position[]>(() => {
    if (!selected) return [];
    return generateLegalMoves(board, selected).map((move) => move.to);
  }, [board, selected]);

  const commitMove = useCallback((current: Board, move: Move) => {
    const piece = getPiece(current, move.from);
    const captured = getPiece(current, move.to);
    if (!piece) return current;

    const next = applyMove(current, move.from, move.to);
    setHistory((prev) => [...prev, { move, piece, captured }]);
    setBoard(next);
    setTurn((side) => (side === "red" ? "black" : "red"));
    return next;
  }, []);

  const selectSquare = useCallback(
    (pos: Position) => {
      if (result !== "playing" || turn !== PLAYER_SIDE || thinking) return;

      if (selected && legalTargets.some((t) => samePosition(t, pos))) {
        commitMove(board, { from: selected, to: pos });
        setSelected(null);
        return;
      }

      const piece = getPiece(board, pos);
      if (piece && piece.side === PLAYER_SIDE) {
        setSelected(pos);
      } else {
        setSelected(null);
      }
    },
    [board, commitMove, legalTargets, result, selected, thinking, turn],
  );

  const restart = useCallback(() => {
    setBoard(createInitialBoard());
    setTurn("red");
    setSelected(null);
    setHistory([]);
  }, []);

  useEffect(() => {
    if (!thinking) return;

    const timer = setTimeout(() => {
      const snapshot = cloneBoard(board);
      const depth = DIFFICULTY_DEPTH[difficulty];
      const move = findBestMove(snapshot, COMPUTER_SIDE, depth);
      if (move) {
        commitMove(snapshot, move);
      }
    }, 300);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [thinking, difficulty]);

  const totalLegalMoves = useMemo(
    () => (result === "playing" ? generateAllLegalMoves(board, turn).length : 0),
    [board, result, turn],
  );

  return {
    board,
    turn,
    selected,
    legalTargets,
    history,
    difficulty,
    setDifficulty,
    thinking,
    result,
    inCheck,
    totalLegalMoves,
    playerSide: PLAYER_SIDE,
    selectSquare,
    restart,
  };
}
