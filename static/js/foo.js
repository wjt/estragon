function startCountdown(selector, arrival, offsetMinutes, yes_url) {
    $(selector).countdown(
      {until: arrival,
       timezone: offsetMinutes,
       expiryUrl: yes_url});
}
