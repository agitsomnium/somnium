// Credentials go directly to Supabase Auth; never put them in profile data or storage.
export function passwordProblem(password, confirmation) {
  if (password.length < 10 || password.length > 128) return "비밀번호는 10~128자로 입력해 주세요.";
  if (password !== confirmation) return "두 비밀번호가 다릅니다. 다시 확인해 주세요.";
  return "";
}
export function authMessage(error) {
  if (error.code === "invalid_credentials") return "이메일 또는 비밀번호가 맞지 않습니다. 비밀번호를 아직 정하지 않았다면 아래 ‘비밀번호 처음 설정 · 잊었어요’를 눌러 주세요.";
  if (error.code === "email_not_confirmed") return "이메일 확인이 필요합니다. ‘비밀번호 처음 설정 · 잊었어요’에서 인증번호를 받아 주세요.";
  if (error.code === "weak_password") return "더 안전한 비밀번호를 입력해 주세요. 흔한 비밀번호는 사용할 수 없습니다.";
  if (error.code === "same_password") return "현재와 다른 비밀번호를 입력해 주세요.";
  return "";
}
export function passwordAuth(auth) {
  return {
    requestCode: (email, signup) => auth.signInWithOtp({ email, options: { shouldCreateUser: signup } }),
    verifyCode: (email, token) => auth.verifyOtp({ email, token, type: "email" }),
    login: (email, password) => auth.signInWithPassword({ email, password }),
    async setPassword(email, password, confirmation) {
      const problem = passwordProblem(password, confirmation);
      if (problem) throw new Error(problem);
      const { data, error } = await auth.getUser();
      if (error || !data.user?.email_confirmed_at || data.user.email?.toLowerCase() !== email.toLowerCase()) {
        throw new Error("이메일을 먼저 인증해 주세요. 인증번호를 다시 받아 확인할 수 있습니다.");
      }
      return auth.updateUser({ password });
    },
  };
}
