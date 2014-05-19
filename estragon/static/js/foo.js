function startCountdown(selector, arrival, offsetMinutes, yes_url) {
    $(selector).countdown(
      {until: arrival,
       format: 'odHMS',
       timezone: offsetMinutes,
       expiryUrl: yes_url});
}
