package cn.qinghe.forum;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name="forum.seed-demo",havingValue="true")
public class DemoSeed implements CommandLineRunner {
    private final ForumService service;
    private final JdbcTemplate db;
    public DemoSeed(ForumService service,JdbcTemplate db) { this.service=service;this.db=db; }
    public void run(String... args) {
        if(!"qinghe_forum_java".equals(db.queryForObject("SELECT DATABASE()",String.class))) throw new IllegalStateException("演示初始化只能用于Java演示库。");
        if(db.queryForObject("SELECT COUNT(*) FROM forum_user WHERE username='java_demo'",Long.class)>0) return;
        String password=System.getenv("FORUM_DEMO_PASSWORD");
        if(password==null) throw new IllegalStateException("需要外部演示账号密码。");
        long author=service.register("java_demo","青禾同学",password,password);
        long category=ForumService.id(service.categories().get(0),"id");
        service.create(author,category,"欢迎来到青禾校园，一起开启Java版论坛","这里是我们的校园交流空间。你可以分享学习经验、讨论校园生活，也可以发布自己的问题。欢迎友善交流！");
        service.create(author,category,"期末复习有哪些实用的方法？","整理知识框架、做错题记录，也别忘了合理安排休息时间。分享一下你的复习计划吧。生活里的每个小经验，都可能帮到另一位同学。");
    }
}
