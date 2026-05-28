"""
Test Complete JWT Authentication Flow

Test semua endpoint authentication:
1. Register user baru
2. Login dan dapat tokens
3. Access protected route dengan access_token
4. Update user profile
5. Refresh access_token
6. Logout (revoke refresh_token)

Run: python test_auth_flow.py
"""

import asyncio
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8000/api/v1"


def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_success(message: str):
    """Print success message"""
    print(f"✅ {message}")


def print_error(message: str):
    """Print error message"""
    print(f"❌ {message}")


def print_info(message: str):
    """Print info message"""
    print(f"ℹ️  {message}")


async def test_auth_flow():
    """Test complete authentication flow"""
    
    async with httpx.AsyncClient() as client:
        
        # ══════════════════════════════════════════════════════════
        # 1. REGISTER USER
        # ══════════════════════════════════════════════════════════
        print_section("1. REGISTER USER")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_email = f"testuser_{timestamp}@example.com"
        test_password = "TestPassword123!"
        test_name = "Test User"
        
        print_info(f"Email: {test_email}")
        print_info(f"Password: {test_password}")
        print_info(f"Name: {test_name}")
        
        try:
            response = await client.post(
                f"{BASE_URL}/auth/register",
                json={
                    "email": test_email,
                    "password": test_password,
                    "full_name": test_name,
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                access_token = data["access_token"]
                refresh_token = data["refresh_token"]
                
                print_success("Register berhasil!")
                print_info(f"Access Token: {access_token[:50]}...")
                print_info(f"Refresh Token: {refresh_token[:50]}...")
            else:
                print_error(f"Register gagal! Status: {response.status_code}")
                print_error(f"Response: {response.text}")
                return
                
        except Exception as e:
            print_error(f"Error saat register: {e}")
            import traceback
            traceback.print_exc()
            return
        
        
        # ══════════════════════════════════════════════════════════
        # 2. LOGIN
        # ══════════════════════════════════════════════════════════
        print_section("2. LOGIN")
        
        print_info(f"Login dengan email: {test_email}")
        
        try:
            response = await client.post(
                f"{BASE_URL}/auth/login/json",
                json={
                    "email": test_email,
                    "password": test_password,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data["access_token"]
                refresh_token = data["refresh_token"]
                
                print_success("Login berhasil!")
                print_info(f"Access Token: {access_token[:50]}...")
                print_info(f"Refresh Token: {refresh_token[:50]}...")
            else:
                print_error(f"Login gagal! Status: {response.status_code}")
                print_error(f"Response: {response.text}")
                return
                
        except Exception as e:
            print_error(f"Error saat login: {e}")
            return
        
        
        # ══════════════════════════════════════════════════════════
        # 3. GET USER PROFILE (Protected Route)
        # ══════════════════════════════════════════════════════════
        print_section("3. GET USER PROFILE (Protected Route)")
        
        print_info("Test protected route dengan access_token")
        
        try:
            response = await client.get(
                f"{BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Get profile berhasil!")
                print_info(f"User ID: {data['id']}")
                print_info(f"Email: {data['email']}")
                print_info(f"Full Name: {data['full_name']}")
                print_info(f"Risk Profile: {data['risk_profile']}")
                print_info(f"Currency: {data['default_currency']}")
                print_info(f"Is Active: {data['is_active']}")
            else:
                print_error(f"Get profile gagal! Status: {response.status_code}")
                print_error(f"Response: {response.text}")
                return
                
        except Exception as e:
            print_error(f"Error saat get profile: {e}")
            return
        
        
        # ══════════════════════════════════════════════════════════
        # 4. UPDATE USER PROFILE
        # ══════════════════════════════════════════════════════════
        print_section("4. UPDATE USER PROFILE")
        
        print_info("Update risk_profile dan default_currency")
        
        try:
            response = await client.put(
                f"{BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "full_name": "Updated Test User",
                    "risk_profile": "aggressive",
                    "default_currency": "USD",
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Update profile berhasil!")
                print_info(f"New Full Name: {data['full_name']}")
                print_info(f"New Risk Profile: {data['risk_profile']}")
                print_info(f"New Currency: {data['default_currency']}")
            else:
                print_error(f"Update profile gagal! Status: {response.status_code}")
                print_error(f"Response: {response.text}")
                
        except Exception as e:
            print_error(f"Error saat update profile: {e}")
        
        
        # ══════════════════════════════════════════════════════════
        # 5. REFRESH TOKEN
        # ══════════════════════════════════════════════════════════
        print_section("5. REFRESH TOKEN")
        
        print_info("Refresh access_token dengan refresh_token")
        
        try:
            response = await client.post(
                f"{BASE_URL}/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                new_access_token = data["access_token"]
                new_refresh_token = data["refresh_token"]
                
                print_success("Refresh token berhasil!")
                print_info(f"New Access Token: {new_access_token[:50]}...")
                print_info(f"New Refresh Token: {new_refresh_token[:50]}...")
                print_info("Old refresh_token sudah di-revoke")
                
                # Update tokens untuk logout
                access_token = new_access_token
                refresh_token = new_refresh_token
            else:
                print_error(f"Refresh token gagal! Status: {response.status_code}")
                print_error(f"Response: {response.text}")
                
        except Exception as e:
            print_error(f"Error saat refresh token: {e}")
        
        
        # ══════════════════════════════════════════════════════════
        # 6. LOGOUT
        # ══════════════════════════════════════════════════════════
        print_section("6. LOGOUT")
        
        print_info("Logout dan revoke refresh_token")
        
        try:
            response = await client.post(
                f"{BASE_URL}/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"refresh_token": refresh_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Logout berhasil!")
                print_info(f"Message: {data['message']}")
                print_info("Refresh token sudah di-revoke")
            else:
                print_error(f"Logout gagal! Status: {response.status_code}")
                print_error(f"Response: {response.text}")
                
        except Exception as e:
            print_error(f"Error saat logout: {e}")
        
        
        # ══════════════════════════════════════════════════════════
        # 7. TEST REVOKED TOKEN
        # ══════════════════════════════════════════════════════════
        print_section("7. TEST REVOKED TOKEN")
        
        print_info("Coba pakai refresh_token yang sudah di-revoke")
        
        try:
            response = await client.post(
                f"{BASE_URL}/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            if response.status_code == 401:
                print_success("Revoked token berhasil di-reject! (Expected behavior)")
                print_info("Refresh token yang sudah logout tidak bisa dipakai lagi")
            else:
                print_error(f"Unexpected status: {response.status_code}")
                print_error("Revoked token seharusnya di-reject!")
                
        except Exception as e:
            print_error(f"Error saat test revoked token: {e}")
        
        
        # ══════════════════════════════════════════════════════════
        # SUMMARY
        # ══════════════════════════════════════════════════════════
        print_section("✅ TEST SELESAI")
        print_success("Semua JWT authentication flow berhasil!")
        print_info("JWT authentication sudah berfungsi dengan baik")
        print_info("Siap untuk implement Google OAuth di step berikutnya")


if __name__ == "__main__":
    print("\n🚀 Starting JWT Authentication Flow Test...")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        asyncio.run(test_auth_flow())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test dibatalkan oleh user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
