package cn.qinghe.forum;

import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.*;
import static org.springframework.security.test.web.servlet.response.SecurityMockMvcResultMatchers.*;

@SpringBootTest(properties={"spring.datasource.url=jdbc:mysql://127.0.0.1:${FORUM_DB_PORT:3306}/test_qinghe_forum_java?useUnicode=true&characterEncoding=UTF-8&connectionTimeZone=UTC"})
@AutoConfigureMockMvc
@Transactional
@EnabledIfEnvironmentVariable(named="FORUM_RUN_DB_TESTS",matches="1")
class ForumIntegrationTest {
    @Autowired MockMvc mvc;
    @Autowired ForumService service;
    @Autowired JdbcTemplate db;
    long alice,bob,category,postId;
    final String password="CampusTest!2026";
    @BeforeEach void seed() {
        assertEquals("test_qinghe_forum_java",db.queryForObject("SELECT DATABASE()",String.class));
        alice=service.register("alice_test","甲同学",password,password);
        bob=service.register("bob_test","乙同学",password,password);
        category=ForumService.id(service.categories().get(0),"id");
        postId=service.create(alice,category,"Java功能测试标题","用于搜索的独特正文");
    }
    @Test void homeAndCategoriesRender() throws Exception { mvc.perform(get("/")).andExpect(status().isOk()).andExpect(content().string(org.hamcrest.Matchers.containsString("Java功能测试标题"))); }
    @Test void registrationCreatesHashedPasswordAndLogsIn() throws Exception {
        mvc.perform(post("/register/").with(csrf()).param("username","new_test").param("nickname","新同学").param("password1",password).param("password2",password)).andExpect(status().is3xxRedirection()).andExpect(authenticated().withUsername("new_test"));
        assertTrue(db.queryForObject("SELECT password FROM forum_user WHERE username='new_test'",String.class).startsWith("$2a$12$"));
    }
    @Test void duplicateRegistrationRejected() throws Exception { mvc.perform(post("/register/").with(csrf()).param("username","alice_test").param("password1",password).param("password2",password)).andExpect(status().isBadRequest()); }
    @Test void loginValidPassword() throws Exception { mvc.perform(post("/login/").with(csrf()).param("username","alice_test").param("password",password)).andExpect(status().is3xxRedirection()).andExpect(authenticated().withUsername("alice_test")); }
    @Test void loginWrongPassword() throws Exception { mvc.perform(post("/login/").with(csrf()).param("username","alice_test").param("password","wrong")).andExpect(redirectedUrl("/login/?error")).andExpect(unauthenticated()); }
    @Test void logoutClearsAuthentication() throws Exception { mvc.perform(post("/logout/").with(user("alice_test")).with(csrf())).andExpect(status().is3xxRedirection()).andExpect(unauthenticated()); }
    @Test void accountIdentityIsolated() throws Exception { mvc.perform(get("/account/me/").with(user("bob_test"))).andExpect(jsonPath("$.id").value(bob)).andExpect(jsonPath("$.username").value("bob_test")); }
    @Test void anonymousCannotPost() throws Exception { mvc.perform(post("/posts/new/").with(csrf()).param("title","attempt").param("body","body").param("category",""+category)).andExpect(status().is3xxRedirection()); }
    @Test void anonymousCannotOpenProtectedForm() throws Exception { mvc.perform(get("/posts/new/")).andExpect(status().is3xxRedirection()); }
    @Test void csrfRequired() throws Exception { mvc.perform(post("/posts/new/").with(user("alice_test"))).andExpect(status().isForbidden()); }
    @Test void createPostPersistsOwner() throws Exception { mvc.perform(post("/posts/new/").with(user("bob_test")).with(csrf()).param("category",""+category).param("title","新帖").param("body","正文")).andExpect(status().is3xxRedirection());assertEquals(bob,db.queryForObject("SELECT author_id FROM forum_post WHERE title='新帖'",Long.class)); }
    @Test void detailRendersContent() throws Exception { mvc.perform(get("/posts/"+postId+"/")).andExpect(status().isOk()).andExpect(content().string(org.hamcrest.Matchers.containsString("独特正文"))); }
    @Test void editingOwnPostWorks() throws Exception { mvc.perform(post("/posts/"+postId+"/edit/").with(user("alice_test")).with(csrf()).param("category",""+category).param("title","改后标题").param("body","改后正文")).andExpect(status().is3xxRedirection());assertEquals("改后标题",service.post(postId).get("title")); }
    @Test void cannotEditOthersPost() throws Exception { mvc.perform(post("/posts/"+postId+"/edit/").with(user("bob_test")).with(csrf()).param("category",""+category).param("title","越权").param("body","越权")).andExpect(status().isForbidden());assertEquals("Java功能测试标题",service.post(postId).get("title")); }
    @Test void cannotDeleteOthersPost() throws Exception { mvc.perform(post("/posts/"+postId+"/delete/").with(user("bob_test")).with(csrf())).andExpect(status().isForbidden()); }
    @Test void commentAndReplyPersist() throws Exception {
        mvc.perform(post("/posts/"+postId+"/comments/").with(user("bob_test")).with(csrf()).param("body","第一条评论")).andExpect(status().is3xxRedirection());
        long commentId=ForumService.id(service.comments(postId).get(0),"id");
        service.comment(postId,alice,"回复评论",commentId);
        mvc.perform(get("/posts/"+postId+"/")).andExpect(status().isOk()).andExpect(content().string(org.hamcrest.Matchers.containsString("回复评论")));
        assertEquals(2,service.comments(postId).size());
    }
    @Test void replyCannotCrossPosts() { service.comment(postId,alice,"原评论",null);long c=ForumService.id(service.comments(postId).get(0),"id");long other=service.create(bob,category,"另外帖子","内容");assertThrows(org.springframework.web.server.ResponseStatusException.class,()->service.comment(other,bob,"跨帖回复",c)); }
    @Test void commentDeletionKeepsReplies() { service.comment(postId,alice,"原评论",null);long c=ForumService.id(service.comments(postId).get(0),"id");service.comment(postId,bob,"保留的回复",c);service.deleteComment(c,alice);assertEquals(2,service.comments(postId).size());assertEquals("",service.comments(postId).get(0).get("body"));assertEquals(1L,((Number)service.post(postId).get("comment_count")).longValue()); }
    @Test void cannotDeleteOthersComment() throws Exception { service.comment(postId,alice,"评论",null);long c=ForumService.id(service.comments(postId).get(0),"id");mvc.perform(post("/comments/"+c+"/delete/").with(user("bob_test")).with(csrf())).andExpect(status().isForbidden()); }
    @Test void likeIsIdempotentAndCanCancel() throws Exception { for(int i=0;i<2;i++)mvc.perform(post("/posts/"+postId+"/like/").with(user("bob_test")).with(csrf()).header("Accept","application/json").param("action","like")).andExpect(status().isOk()).andExpect(jsonPath("$.count").value(1));mvc.perform(post("/posts/"+postId+"/like/").with(user("bob_test")).with(csrf()).header("Accept","application/json").param("action","unlike")).andExpect(jsonPath("$.count").value(0)); }
    @Test void invalidLikeActionRejected() throws Exception { mvc.perform(post("/posts/"+postId+"/like/").with(user("alice_test")).with(csrf()).param("action","toggle")).andExpect(status().isBadRequest()); }
    @Test void titleAndBodySearchAndEmptyState() throws Exception { for(String q:List.of("Java功能","独特正文")) mvc.perform(get("/").param("q",q)).andExpect(status().isOk()).andExpect(content().string(org.hamcrest.Matchers.containsString("Java功能测试标题")));mvc.perform(get("/").param("q","无匹配_987" )).andExpect(content().string(org.hamcrest.Matchers.containsString("暂时没有找到相关帖子"))); }
    @Test void categoryAndHotSortingRender() throws Exception { String slug=(String)service.category(category).get("slug");mvc.perform(get("/").param("category",slug).param("sort","hot")).andExpect(status().isOk()); }
    @Test void profileCanOnlyEditCurrentUser() throws Exception { mvc.perform(post("/settings/profile/").with(user("bob_test")).with(csrf()).param("nickname","新昵称").param("bio","新简介")).andExpect(status().is3xxRedirection());assertEquals("新昵称",service.user(bob).get("nickname"));assertEquals("甲同学",service.user(alice).get("nickname")); }
    @Test void deleteOwnPostCascadesCommentsAndLikes() { service.comment(postId,alice,"原评论",null);long c=ForumService.id(service.comments(postId).get(0),"id");service.comment(postId,bob,"回复",c);service.like(postId,bob,"like");service.deletePost(postId,alice);assertEquals(0L,db.queryForObject("SELECT COUNT(*) FROM forum_comment WHERE post_id=?",Long.class,postId));assertEquals(0L,db.queryForObject("SELECT COUNT(*) FROM forum_post_like WHERE post_id=?",Long.class,postId)); }
    @Test void pageEscapesUserHtml() throws Exception { service.edit(postId,alice,category,"<script>alert(1)</script>","<img src=x onerror=alert(1)>");mvc.perform(get("/posts/"+postId+"/")).andExpect(content().string(org.hamcrest.Matchers.containsString("&lt;script&gt;"))).andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("<script>alert(1)</script>")))); }
    @Test void missingPostIs404() throws Exception { mvc.perform(get("/posts/999999999/")).andExpect(status().isNotFound()); }
    @Test void publicationTimeMatchesRealClock() {
        var stamp=(java.sql.Timestamp)service.post(postId).get("created_at");
        assertTrue(Math.abs(stamp.toInstant().toEpochMilli()-System.currentTimeMillis())<10000,"数据库会话与JDBC时区必须一致，不能偏移8小时。");
    }
}
