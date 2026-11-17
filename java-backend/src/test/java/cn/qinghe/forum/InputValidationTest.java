package cn.qinghe.forum;

import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.server.ResponseStatusException;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class InputValidationTest {
    private final JdbcTemplate db=mock(JdbcTemplate.class);
    private final ForumService service=new ForumService(db,new BCryptPasswordEncoder(12));
    @Test void emptyPostTextRejected() { assertThrows(ResponseStatusException.class,()->ForumService.text(" \n",100,"标题")); }
    @Test void longBodyRejected() { assertThrows(ResponseStatusException.class,()->ForumService.text("字".repeat(10001),10000,"正文")); }
    @Test void supplementaryCharactersCountedAsOne() { assertEquals("😀",ForumService.text("😀",1,"内容")); }
    @Test void passwordsMustMatch() { assertThrows(ResponseStatusException.class,()->service.register("student","","ValidPassword!8","different"));verifyNoInteractions(db); }
    @Test void numericPasswordRejected() { assertThrows(ResponseStatusException.class,()->service.register("student","","123456789","123456789"));verifyNoInteractions(db); }
    @Test void commonPasswordRejected() { assertThrows(ResponseStatusException.class,()->service.register("student","","password123","password123"));verifyNoInteractions(db); }
    @Test void shortPasswordRejected() { assertThrows(ResponseStatusException.class,()->service.register("student","","abc","abc"));verifyNoInteractions(db); }
    @Test void bcryptByteLimitEnforced() { String p="密".repeat(30);assertThrows(ResponseStatusException.class,()->service.register("student","",p,p));verifyNoInteractions(db); }
    @Test void unsafeUsernameRejected() { assertThrows(ResponseStatusException.class,()->service.register("<script>","","ValidPassword!8","ValidPassword!8"));verifyNoInteractions(db); }
    @Test void profileLengthEnforced() { assertThrows(ResponseStatusException.class,()->service.profile(1,"字".repeat(31),""));verifyNoInteractions(db); }
    @Test void bcryptIsSaltedAndVerifiable() { var encoder=new BCryptPasswordEncoder(12);String one=encoder.encode("ValidPassword!8"),two=encoder.encode("ValidPassword!8");assertNotEquals(one,two);assertTrue(encoder.matches("ValidPassword!8",one));assertFalse(encoder.matches("wrong",one)); }
}
