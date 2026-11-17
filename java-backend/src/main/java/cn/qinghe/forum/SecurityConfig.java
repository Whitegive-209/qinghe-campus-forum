package cn.qinghe.forum;

import org.springframework.context.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.*;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {
    @Bean PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(12); }
    @Bean UserDetailsService userDetailsService(JdbcTemplate db) {
        return name->{
            var rows=db.queryForList("SELECT username,password FROM forum_user WHERE username=?",name);
            if(rows.isEmpty()) throw new UsernameNotFoundException("用户名或密码不正确");
            var row=rows.get(0);
            return User.withUsername((String)row.get("username")).password((String)row.get("password")).roles("USER").build();
        };
    }
    @Bean SecurityFilterChain security(HttpSecurity http) throws Exception {
        http.authorizeHttpRequests(auth->auth
            .requestMatchers("/","/login/","/register/","/health/","/static/**","/error").permitAll()
            .requestMatchers(new org.springframework.security.web.util.matcher.RegexRequestMatcher("^/(users|posts)/[0-9]+/$","GET")).permitAll()
            .anyRequest().authenticated())
            .formLogin(login->login.loginPage("/login/").loginProcessingUrl("/login/").defaultSuccessUrl("/",false).failureUrl("/login/?error"))
            .logout(logout->logout.logoutUrl("/logout/").logoutSuccessUrl("/?loggedout"));
        return http.build();
    }
}
