"use client";

import { XiangqiBoard } from "./components/Board";
import { GameStatusBar } from "./components/GameStatusBar";
import { MoveHistory } from "./components/MoveHistory";
import { useXiangqiGame } from "./hooks/useXiangqiGame";

export default function Home() {
  const {
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
    selectSquare,
    restart,
  } = useXiangqiGame();

  return (
    <main className="flex min-h-screen flex-col items-center gap-6 bg-gradient-to-b from-amber-50 to-amber-100 p-6">
      <h1 className="text-2xl font-bold text-neutral-800">中国象棋 · 人机对战</h1>

      <div className="flex flex-col items-center gap-4 md:flex-row md:items-start">
        <div className="flex flex-col items-center gap-4">
          <GameStatusBar
            turn={turn}
            result={result}
            inCheck={inCheck}
            thinking={thinking}
            difficulty={difficulty}
            onDifficultyChange={setDifficulty}
            onRestart={restart}
          />
          <XiangqiBoard board={board} selected={selected} legalTargets={legalTargets} onSelect={selectSquare} />
          <p className="text-xs text-neutral-500">你执红先行，点击棋子选中，再点击目标位置落子。</p>
        </div>

        <MoveHistory history={history} />
      </div>
    </main>
  );
}
