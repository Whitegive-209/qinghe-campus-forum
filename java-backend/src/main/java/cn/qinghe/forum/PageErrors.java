package cn.qinghe.forum;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.bind.annotation.*;
import org.springframework.ui.Model;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.dao.DataIntegrityViolationException;

@ControllerAdvice
public class PageErrors {
    @ExceptionHandler(ResponseStatusException.class)
    String status(ResponseStatusException error,HttpServletResponse response,Model model) {
        response.setStatus(error.getStatusCode().value());
        model.addAttribute("errorText",error.getReason());return "problem";
    }
    @ExceptionHandler(DataIntegrityViolationException.class)
    String conflict(HttpServletResponse response,Model model) {
        response.setStatus(409);model.addAttribute("errorText","内容已发生变化，请刷新页面后重试。");return "problem";
    }
}
