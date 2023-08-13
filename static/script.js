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

var start;

// Function to set the value of the input field with the timestamp when the page finishes loading
function setLoadTimeInput() {
    start = new Date().getTime(); // Get the current timestamp in milliseconds
}

// Call the setLoadTimeInput function when the page finishes loading
window.addEventListener('load', setLoadTimeInput);

// Function to convert seconds to hours, minutes, and seconds
function secondsToHoursMinutesSeconds(seconds) {
    var hours = Math.floor(seconds / 3600);
    var remainingSeconds = seconds % 3600;
    var minutes = Math.floor(remainingSeconds / 60);
    var secs = remainingSeconds % 60;
    // Create the formatted time string, removing parts where the value is 0
    var timeString = '';
    if (hours > 0) {
        timeString += hours + ' hours ';
    }
    if (minutes > 0) {
        timeString += minutes + ' minutes ';
    }
    if (secs > 0 || (hours === 0 && minutes === 0)) {
        timeString += secs + ' seconds';
    }

    return timeString;
}

// Event listener for form submission
document.getElementById('quiz-form').addEventListener('submit', function(e) {
    e.preventDefault();

    // Calculate the time difference between the current timestamp and the timestamp when the page was loaded
    var end = new Date().getTime();
    var timeSpentSeconds = Math.floor((end - start) / 1000); // Calculate time difference in seconds

    // Convert seconds to hours, minutes, and seconds
    var timeSpentFormatted = secondsToHoursMinutesSeconds(timeSpentSeconds);

    // Set the value of the hidden input field with the time difference in hours, minutes, and seconds
    document.getElementById('timeTaken').value = timeSpentFormatted;

    // Uncomment the following line to submit the form without AJAX
    this.submit();

    // Now you can submit the form or handle the timeSpentFormatted value as needed
});

