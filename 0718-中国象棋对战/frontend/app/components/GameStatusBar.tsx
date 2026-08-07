import { DIFFICULTY_LABELS } from "@/lib/xiangqi/ai/difficulty";
import { Difficulty, GameResult, Side } from "@/lib/xiangqi/types";

interface GameStatusBarProps {
  turn: Side;
  result: GameResult;
  inCheck: boolean;
  thinking: boolean;
  difficulty: Difficulty;
  onDifficultyChange: (d: Difficulty) => void;
  onRestart: () => void;
}

function resultText(result: GameResult): string | null {
  if (result === "redWins") return "🎉 红方（玩家）获胜！";
  if (result === "blackWins") return "💻 黑方（电脑）获胜！";
  return null;
}

export function GameStatusBar({
  turn,
  result,
  inCheck,
  thinking,
  difficulty,
  onDifficultyChange,
  onRestart,
}: GameStatusBarProps) {
  const finished = resultText(result);

  return (
    <div className="flex w-full max-w-[560px] flex-col gap-3">
      <div className="flex items-center justify-between rounded-lg bg-white/80 px-4 py-3 shadow">
        <div className="text-sm font-medium">
          {finished ? (
            <span className="text-lg font-bold">{finished}</span>
          ) : (
            <span>
              当前回合：
              <span className={turn === "red" ? "text-red-700" : "text-neutral-800"}>
                {turn === "red" ? "红方（你）" : "黑方（电脑）"}
              </span>
              {thinking && <span className="ml-2 text-neutral-500">电脑思考中…</span>}
              {inCheck && !thinking && <span className="ml-2 font-bold text-red-600">将军！</span>}
            </span>
          )}
        </div>

        <button
          onClick={onRestart}
          className="rounded bg-neutral-800 px-3 py-1 text-sm text-white hover:bg-neutral-700"
        >
          重新开始
        </button>
      </div>

      <div className="flex items-center gap-2 rounded-lg bg-white/80 px-4 py-3 shadow">
        <span className="text-sm text-neutral-600">电脑难度：</span>
        {(Object.keys(DIFFICULTY_LABELS) as Difficulty[]).map((level) => (
          <button
            key={level}
            onClick={() => onDifficultyChange(level)}
            className={`rounded px-3 py-1 text-sm ${
              difficulty === level
                ? "bg-blue-600 text-white"
                : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
            }`}
          >
            {DIFFICULTY_LABELS[level]}
          </button>
        ))}
      </div>
    </div>
  );
}
