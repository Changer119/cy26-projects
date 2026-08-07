/* 股票投资教学工作区 — 轻量测验组件
   用法：
   <div class="quiz-q">
     <div class="prompt">问题文本</div>
     <div class="quiz-options">
       <button class="quiz-option" data-correct="false">选项</button>
       <button class="quiz-option" data-correct="true">选项</button>
     </div>
     <div class="quiz-feedback"></div>
   </div>
   注意：为避免格式暴露答案，每题所有选项应保持长度/字数大致相同。
*/
(function () {
  function initQuiz(root) {
    root.querySelectorAll(".quiz-q").forEach(function (q) {
      const options = q.querySelectorAll(".quiz-option");
      const feedback = q.querySelector(".quiz-feedback");
      let answered = false;

      options.forEach(function (opt) {
        opt.addEventListener("click", function () {
          if (answered) return;
          answered = true;
          const isCorrect = opt.getAttribute("data-correct") === "true";

          options.forEach(function (o) {
            o.disabled = true;
            if (o.getAttribute("data-correct") === "true") {
              o.classList.add("correct");
            } else if (o === opt) {
              o.classList.add("incorrect");
            }
          });

          if (feedback) {
            feedback.classList.add("show", isCorrect ? "correct" : "incorrect");
            feedback.textContent = isCorrect
              ? (feedback.dataset.correctText || "回答正确。")
              : (feedback.dataset.incorrectText || "再想想 —— 正确答案已高亮显示。");
          }
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initQuiz(document);
  });
})();
