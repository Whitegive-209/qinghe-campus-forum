package cn.qinghe.forum;

import java.nio.charset.StandardCharsets;
import java.util.*;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class ForumService {
    private final JdbcTemplate db;
    private final PasswordEncoder encoder;
    public ForumService(JdbcTemplate db, PasswordEncoder encoder) { this.db=db; this.encoder=encoder; }
    static ResponseStatusException bad(String text) { return new ResponseStatusException(HttpStatus.BAD_REQUEST,text); }
    static long id(Map<String,Object> row,String key) { return ((Number)row.get(key)).longValue(); }
    static String text(String value,int max,String label) {
        String s=value==null?"":value.strip();
        if(s.isEmpty()||s.codePointCount(0,s.length())>max) throw bad(label+"不能为空，且不能超过"+max+"字。");
        return s;
    }
    Map<String,Object> one(String sql,Object...args) {
        var rows=db.queryForList(sql,args);
        if(rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,"没有找到相关内容。");
        return rows.get(0);
    }
    public Map<String,Object> user(long id) {
        return one("SELECT id,username,nickname,bio,created_at,COALESCE(NULLIF(nickname,''),username) display_name FROM forum_user WHERE id=?",id);
    }
    public Map<String,Object> userByName(String name) { return user(id(one("SELECT id FROM forum_user WHERE username=?",name),"id")); }
    public List<Map<String,Object>> categories() { return db.queryForList("SELECT * FROM forum_category ORDER BY sort_order,id"); }
    public Map<String,Object> category(long id) { return one("SELECT * FROM forum_category WHERE id=?",id); }
    public long register(String username,String nickname,String password,String confirmation) {
        username=text(username,30,"用户名");
        if(!username.matches("[\\p{L}\\p{N}_@.+-]+")) throw bad("用户名只能包含文字、数字及_@.+-。");
        if(password==null||password.length()<8||password.getBytes(StandardCharsets.UTF_8).length>72) throw bad("密码至少8个字符，且UTF-8编码不超过72字节。");
        if(!password.equals(confirmation)) throw bad("两次输入的密码不一致。");
        if(password.matches("[0-9]+")||Set.of("password","password123","12345678","qwerty123").contains(password.toLowerCase(Locale.ROOT))) throw bad("请使用不常见且不全为数字的密码。");
        nickname=nickname==null?"":nickname.strip();
        if(nickname.length()>30) throw bad("昵称最多30字。");
        try { db.update("INSERT INTO forum_user(username,password,nickname) VALUES (?,?,?)",username,encoder.encode(password),nickname); }
        catch(DuplicateKeyException ex) { throw bad("用户名已经存在。"); }
        return id(one("SELECT id FROM forum_user WHERE username=?",username),"id");
    }
    public void profile(long userId,String nickname,String bio) {
        nickname=nickname==null?"":nickname.strip();bio=bio==null?"":bio.strip();
        if(nickname.length()>30||bio.length()>200) throw bad("昵称最多30字，简介最多200字。");
        db.update("UPDATE forum_user SET nickname=?,bio=? WHERE id=?",nickname,bio,userId);
    }
    private static final String POST_SELECT="""
        SELECT p.*,u.username,u.bio,COALESCE(NULLIF(u.nickname,''),u.username) display_name,
        c.name category_name,c.slug category_slug,
        (SELECT COUNT(*) FROM forum_comment co WHERE co.post_id=p.id AND co.is_deleted=FALSE) comment_count,
        (SELECT COUNT(*) FROM forum_post_like li WHERE li.post_id=p.id) like_count
        FROM forum_post p JOIN forum_user u ON u.id=p.author_id JOIN forum_category c ON c.id=p.category_id
        """;
    public Map<String,Object> listing(String query,String slug,String sort,int page,Long author) {
        query=query==null?"":query.strip();slug=slug==null?"":slug.strip();
        if(query.length()>100) throw bad("关键词最多100字。");
        String where=" WHERE 1=1"; List<Object> args=new ArrayList<>();
        if(!query.isEmpty()) { where+=" AND (LOCATE(LOWER(?),LOWER(p.title))>0 OR LOCATE(LOWER(?),LOWER(p.body))>0)"; args.add(query);args.add(query); }
        if(!slug.isEmpty()) { one("SELECT id FROM forum_category WHERE slug=?",slug);where+=" AND p.category_id=(SELECT id FROM forum_category WHERE slug=?)";args.add(slug); }
        if(author!=null) { where+=" AND p.author_id=?";args.add(author); }
        long count=db.queryForObject("SELECT COUNT(*) FROM forum_post p"+where,Long.class,args.toArray());
        long pages=Math.max(1,(count+19)/20);page=(int)Math.min(Math.max(1,page),pages);
        String order="hot".equals(sort)?" ORDER BY like_count DESC,comment_count DESC,p.created_at DESC,p.id DESC":" ORDER BY p.created_at DESC,p.id DESC";
        args.add(20);args.add((page-1)*20);
        var posts=db.queryForList(POST_SELECT+where+order+" LIMIT ? OFFSET ?",args.toArray());
        return Map.of("posts",posts,"total",count,"page",page,"pages",pages,"q",query,"category",slug,"sort","hot".equals(sort)?"hot":"new");
    }
    public Map<String,Object> post(long id) { return one(POST_SELECT+" WHERE p.id=?",id); }
    public void ownsPost(long id,long owner) {
        if(id(post(id),"author_id")!=owner) throw new ResponseStatusException(HttpStatus.FORBIDDEN,"只能操作自己的帖子。");
    }
    @Transactional
    public long create(long owner,long categoryId,String title,String body) {
        category(categoryId);title=text(title,100,"标题");body=text(body,10000,"正文");
        var keys=new org.springframework.jdbc.support.GeneratedKeyHolder();
        String finalTitle=title,finalBody=body;
        db.update(conn->{var ps=conn.prepareStatement("INSERT INTO forum_post(author_id,category_id,title,body) VALUES (?,?,?,?)",java.sql.Statement.RETURN_GENERATED_KEYS);ps.setLong(1,owner);ps.setLong(2,categoryId);ps.setString(3,finalTitle);ps.setString(4,finalBody);return ps;},keys);
        return Objects.requireNonNull(keys.getKey()).longValue();
    }
    @Transactional
    public void edit(long postId,long owner,long categoryId,String title,String body) {
        ownsPost(postId,owner);category(categoryId);
        db.update("UPDATE forum_post SET category_id=?,title=?,body=?,updated_at=CURRENT_TIMESTAMP(6) WHERE id=? AND author_id=?",categoryId,text(title,100,"标题"),text(body,10000,"正文"),postId,owner);
    }
    @Transactional
    public void deletePost(long postId,long owner) {
        ownsPost(postId,owner);
        db.update("UPDATE forum_comment SET parent_id=NULL WHERE post_id=?",postId);
        db.update("DELETE FROM forum_post WHERE id=? AND author_id=?",postId,owner);
    }
    public List<Map<String,Object>> comments(long postId) {
        return db.queryForList("""
            SELECT co.*,COALESCE(NULLIF(u.nickname,''),u.username) display_name,
            COALESCE(NULLIF(pu.nickname,''),pu.username) parent_name
            FROM forum_comment co JOIN forum_user u ON u.id=co.author_id
            LEFT JOIN forum_comment pa ON pa.id=co.parent_id LEFT JOIN forum_user pu ON pu.id=pa.author_id
            WHERE co.post_id=? ORDER BY co.created_at,co.id
            """,postId);
    }
    @Transactional
    public void comment(long postId,long owner,String body,Long parentId) {
        one("SELECT id FROM forum_post WHERE id=? FOR UPDATE",postId);
        if(parentId!=null&&id(one("SELECT post_id FROM forum_comment WHERE id=?",parentId),"post_id")!=postId) throw bad("回复对象必须在当前帖子中。");
        db.update("INSERT INTO forum_comment(post_id,author_id,parent_id,body) VALUES (?,?,?,?)",postId,owner,parentId,text(body,1000,"评论"));
    }
    @Transactional
    public long deleteComment(long commentId,long owner) {
        var row=one("SELECT author_id,post_id FROM forum_comment WHERE id=?",commentId);
        if(id(row,"author_id")!=owner) throw new ResponseStatusException(HttpStatus.FORBIDDEN,"只能删除自己的评论。");
        db.update("UPDATE forum_comment SET body='',is_deleted=TRUE WHERE id=?",commentId);
        return id(row,"post_id");
    }
    public boolean liked(long postId,long userId) { return db.queryForObject("SELECT COUNT(*) FROM forum_post_like WHERE post_id=? AND user_id=?",Long.class,postId,userId)>0; }
    @Transactional
    public Map<String,Object> like(long postId,long userId,String action) {
        one("SELECT id FROM forum_post WHERE id=? FOR UPDATE",postId);
        if("like".equals(action)) {
            db.update("INSERT INTO forum_post_like(user_id,post_id) VALUES (?,?) ON DUPLICATE KEY UPDATE user_id=VALUES(user_id)",userId,postId);
        } else if("unlike".equals(action)) db.update("DELETE FROM forum_post_like WHERE user_id=? AND post_id=?",userId,postId);
        else throw bad("点赞动作必须为like或unlike。");
        return Map.of("liked",liked(postId,userId),"count",db.queryForObject("SELECT COUNT(*) FROM forum_post_like WHERE post_id=?",Long.class,postId));
    }
}
