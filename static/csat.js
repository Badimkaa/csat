const token = window.CSAT_TOKEN || "";
const lang = window.CSAT_LANG || "en";
const projectKey = window.CSAT_PROJECT_KEY || "";

// Check if project is APIR or APIO
const isSpecialProject = projectKey === "APIR" || projectKey === "APIO";

const MESSAGES = {
  'ru': {
    'comment_label': 'Комментарий',
    'submit_button': 'Отправить',
    'thank_you': 'Спасибо за вашу обратную связь!',
    'error': 'Ошибка, попробуйте позже.',
    'score_required': 'Пожалуйста, поставьте оценку.',
    'comment_required': 'Комментарий обязателен при оценке 4 или ниже.',
    'placeholder_comment': 'Место для комментария'
  },
  'en': {
    'comment_label': 'Comment',
    'submit_button': 'Submit',
    'thank_you': 'Thank you for your feedback!',
    'error': 'Error, please try again.',
    'score_required': 'Please select a score.',
    'comment_required': 'Please add a comment for scores 4 or less.',
    'placeholder_comment': 'Place for comment'
  }
};
const texts = MESSAGES[lang] || MESSAGES['en'];

document.addEventListener("DOMContentLoaded", function() {
  const ticketKey = window.CSAT_ISSUE_KEY || "";

  // Show/hide forms based on project key
  if (isSpecialProject) {
    document.getElementById('csatForm').style.display = 'none';
    document.getElementById('csatFormSpecial').style.display = 'block';
    initializeSpecialForm();
  } else {
    document.getElementById('csatFormSpecial').style.display = 'none';
    document.getElementById('csatForm').style.display = 'block';
    initializeGeneralForm();
  }

  // Display task key in both forms
  if (ticketKey) {
    const taskKeyDiv = document.getElementById('task-key');
    if (taskKeyDiv) {
      taskKeyDiv.textContent = (lang === 'ru' ? 'Задача: ' : 'Task: ') + ticketKey;
    }
    const taskKeyDivSpecial = document.getElementById('task-key-special');
    if (taskKeyDivSpecial) {
      taskKeyDivSpecial.textContent = (lang === 'ru' ? 'Задача: ' : 'Task: ') + ticketKey;
    }
  }

  function setupStars(starsId, scoreInputId, submitBtnId) {
    const starsDiv = document.getElementById(starsId);
    const hiddenScore = document.getElementById(scoreInputId);
    const submitBtn = document.getElementById(submitBtnId);
    let selected = 0;

    function highlight(starIndex) {
      const stars = starsDiv.querySelectorAll('.star');
      stars.forEach((star, idx) => {
        if (idx < starIndex) {
          star.classList.add('hovered');
        } else {
          star.classList.remove('hovered');
        }
      });
    }

    function select(starIndex) {
      selected = starIndex;
      hiddenScore.value = String(selected);
      const stars = starsDiv.querySelectorAll('.star');
      stars.forEach((star, idx) => {
        if (idx < starIndex) {
          star.classList.add('selected');
        } else {
          star.classList.remove('selected');
        }
      });
      submitBtn.disabled = false;
    }

    starsDiv.querySelectorAll('.star').forEach((star, idx) => {
      star.addEventListener('mouseenter', () => highlight(idx + 1));
      star.addEventListener('mouseleave', () => highlight(selected));
      star.addEventListener('click', () => select(idx + 1));
    });
    starsDiv.addEventListener('mouseleave', () => highlight(selected));
  }

  function initializeGeneralForm() {
    document.getElementById('label-comment').textContent = texts.comment_label;
    document.getElementById('commentArea').placeholder = texts.placeholder_comment;
    document.getElementById('submitBtn').textContent = texts.submit_button;

    setupStars('stars', 'scoreInput', 'submitBtn');

    const form = document.getElementById('csatForm');
    const commentArea = document.getElementById('commentArea');
    const hiddenScore = document.getElementById('scoreInput');

    form.onsubmit = async function(event) {
      event.preventDefault();
      const score = Number(hiddenScore.value);
      const comment = commentArea.value.trim();

      if (!score) {
        alert(texts.score_required);
        return;
      }
      if (score <= 4 && !comment) {
        alert(texts.comment_required);
        commentArea.focus();
        return;
      }
      const data = new FormData(form);
      data.set('score', String(score));
      document.getElementById('submitBtn').disabled = true;
      const response = await fetch(`/survey/${token}/submit`, {
        method: "POST",
        body: data
      });
      if (response.ok) {
        const responseDiv = document.getElementById('response');
        responseDiv.textContent = texts.thank_you;
        responseDiv.className = 'csat-response thankyou-title';
        form.style.display = "none";
      } else {
        document.getElementById('response').textContent = texts.error;
        document.getElementById('submitBtn').disabled = false;
      }
    };
  }

  function initializeSpecialForm() {
    document.getElementById('label-comment-special').textContent = texts.comment_label;
    document.getElementById('commentAreaSpecial').placeholder = texts.placeholder_comment;
    document.getElementById('submitBtnSpecial').textContent = texts.submit_button;

    setupStars('stars-special', 'scoreInputSpecial', 'submitBtnSpecial');

    const form = document.getElementById('csatFormSpecial');
    const commentArea = document.getElementById('commentAreaSpecial');
    const hiddenScore = document.getElementById('scoreInputSpecial');

    form.onsubmit = async function(event) {
      event.preventDefault();
      const score = Number(hiddenScore.value);
      const comment = commentArea.value.trim();

      if (!score) {
        alert(texts.score_required);
        return;
      }
      if (score <= 4 && !comment) {
        alert(texts.comment_required);
        commentArea.focus();
        return;
      }
      const data = new FormData(form);
      data.set('score', String(score));
      document.getElementById('submitBtnSpecial').disabled = true;
      const response = await fetch(`/survey/${token}/submit`, {
        method: "POST",
        body: data
      });
      if (response.ok) {
        const responseDiv = document.getElementById('response');
        responseDiv.textContent = texts.thank_you;
        responseDiv.className = 'csat-response thankyou-title';
        form.style.display = "none";
      } else {
        document.getElementById('response').textContent = texts.error;
        document.getElementById('submitBtnSpecial').disabled = false;
      }
    };
  }
});