let quizId;
let quizName;

function openPopup(id, name) {
  document.getElementById('emailPopup').style.display = 'block';
  quizId = id;
  quizName = name;
}

function closePopup() {
  document.getElementById('emailPopup').style.display = 'none';
}

function sendEmail() {
  const recipientEmail = document.getElementById('recipientEmail').value;
  if (recipientEmail) {
    // Call your Flask route to send the email
    fetch(`/send_email/${quizId}/${quizName}/${recipientEmail}`)
    .then(response => {
      if (response.ok) {
        return response.text();
      } else {
        throw new Error('Error sending email');
      }
    })
    .then(data => {
      // Instead of alerting the user, reload the quizzes page
      window.location.href = quizUrl;
    })
    .catch((error) => {
      console.error('Error:', error);
      alert('Error sending email');
    });
  } else {
    alert('Please enter a recipient email address');
  }
}
