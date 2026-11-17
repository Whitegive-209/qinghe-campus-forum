package cn.qinghe.forum;

import java.util.*;
import jakarta.servlet.http.*;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.AuthorityUtils;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

@Controller
public class ForumController {
    private final ForumService forum;
    private final JdbcTemplate db;
    public ForumController(ForumService forum,JdbcTemplate db) { this.forum=forum;this.db=db; }
    long viewerId(Authentication auth) {
        if(auth==null||!auth.isAuthenticated()) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请先登录。");
        return ForumService.id(forum.userByName(auth.getName()),"id");
    }
    @ModelAttribute
    void shared(Model model,Authentication auth) {
        model.addAttribute("signedIn",auth!=null&&auth.isAuthenticated());
        model.addAttribute("viewer",auth==null?null:forum.userByName(auth.getName()));
    }
    @GetMapping("/")
    String home(@RequestParam(defaultValue="") String q,@RequestParam(defaultValue="") String category,
                @RequestParam(defaultValue="new") String sort,@RequestParam(defaultValue="1") int page,Model m) {
        m.addAllAttributes(forum.listing(q,category,sort,page,null));m.addAttribute("categories",forum.categories());return "home";
    }
    @GetMapping("/health/") @ResponseBody
    Map<String,String> health() { db.queryForObject("SELECT 1",Integer.class);return Map.of("status","ok","backend","java"); }
    @GetMapping("/login/") String login() { return "login"; }
    @GetMapping("/register/") String register() { return "register"; }
    @PostMapping("/register/")
    String register(@RequestParam String username,@RequestParam(defaultValue="") String nickname,
                    @RequestParam String password1,@RequestParam String password2,
                    HttpServletRequest request,HttpServletResponse response,RedirectAttributes flash) {
        forum.register(username,nickname,password1,password2);
        if(request.getSession(false)!=null) request.changeSessionId();
        var context=SecurityContextHolder.createEmptyContext();
        context.setAuthentication(new UsernamePasswordAuthenticationToken(username,null,AuthorityUtils.createAuthorityList("ROLE_USER")));
        SecurityContextHolder.setContext(context);
        new HttpSessionSecurityContextRepository().saveContext(context,request,response);
        flash.addFlashAttribute("message","注册成功，欢迎来到青禾校园！");return "redirect:/";
    }
    @GetMapping("/account/me/") @ResponseBody
    Map<String,Object> me(Authentication auth) { var user=forum.user(viewerId(auth));return Map.of("id",user.get("id"),"username",user.get("username")); }
    @GetMapping("/users/{id}/")
    String profile(@PathVariable long id,@RequestParam(defaultValue="1") int page,Model m) {
        m.addAttribute("profile",forum.user(id));m.addAllAttributes(forum.listing("","","new",page,id));return "profile";
    }
    @GetMapping("/settings/profile/") String settings() { return "settings"; }
    @PostMapping("/settings/profile/")
    String settings(Authentication auth,@RequestParam(defaultValue="") String nickname,@RequestParam(defaultValue="") String bio,RedirectAttributes flash) {
        long id=viewerId(auth);forum.profile(id,nickname,bio);flash.addFlashAttribute("message","个人资料已保存。");return "redirect:/users/"+id+"/";
    }
    @GetMapping("/posts/new/")
    String newPost(Authentication auth,Model m) { viewerId(auth);m.addAttribute("categories",forum.categories());m.addAttribute("editing",false);return "post-form"; }
    @PostMapping("/posts/new/")
    String create(Authentication auth,@RequestParam long category,@RequestParam String title,@RequestParam String body,RedirectAttributes flash) {
        long id=forum.create(viewerId(auth),category,title,body);flash.addFlashAttribute("message","帖子已发布。");return "redirect:/posts/"+id+"/";
    }
    @GetMapping("/posts/{id}/")
    String detail(@PathVariable long id,Authentication auth,Model m) {
        m.addAttribute("post",forum.post(id));m.addAttribute("comments",forum.comments(id));
        m.addAttribute("liked",auth!=null&&forum.liked(id,viewerId(auth)));return "detail";
    }
    @GetMapping("/posts/{id}/edit/")
    String edit(@PathVariable long id,Authentication auth,Model m) {
        forum.ownsPost(id,viewerId(auth));m.addAttribute("post",forum.post(id));m.addAttribute("categories",forum.categories());m.addAttribute("editing",true);return "post-form";
    }
    @PostMapping("/posts/{id}/edit/")
    String edit(@PathVariable long id,Authentication auth,@RequestParam long category,@RequestParam String title,@RequestParam String body,RedirectAttributes flash) {
        forum.edit(id,viewerId(auth),category,title,body);flash.addFlashAttribute("message","帖子修改已保存。");return "redirect:/posts/"+id+"/";
    }
    @GetMapping("/posts/{id}/delete/")
    String delete(@PathVariable long id,Authentication auth,Model m) { forum.ownsPost(id,viewerId(auth));m.addAttribute("post",forum.post(id));return "delete"; }
    @PostMapping("/posts/{id}/delete/")
    String delete(@PathVariable long id,Authentication auth,RedirectAttributes flash) { forum.deletePost(id,viewerId(auth));flash.addFlashAttribute("message","帖子已删除。");return "redirect:/"; }
    @PostMapping("/posts/{id}/comments/")
    String comment(@PathVariable long id,Authentication auth,@RequestParam String body,@RequestParam(required=false) Long parent,RedirectAttributes flash) {
        forum.comment(id,viewerId(auth),body,parent);flash.addFlashAttribute("message","评论已发布。");return "redirect:/posts/"+id+"/#comments";
    }
    @PostMapping("/comments/{id}/delete/")
    String deleteComment(@PathVariable long id,Authentication auth,RedirectAttributes flash) {
        long postId=forum.deleteComment(id,viewerId(auth));flash.addFlashAttribute("message","评论已删除，已有回复保留。");return "redirect:/posts/"+postId+"/#comments";
    }
    @PostMapping("/posts/{id}/like/")
    Object like(@PathVariable long id,Authentication auth,@RequestParam String action,HttpServletRequest request) {
        var result=forum.like(id,viewerId(auth),action);
        if(Optional.ofNullable(request.getHeader("Accept")).orElse("").contains("application/json"))return org.springframework.http.ResponseEntity.ok(result);
        return "redirect:/posts/"+id+"/";
    }
}
