# 🔀 Merge Guide: Security Backend + Role-Based Frontend

## Overview

**Goal:** Integrate your security backend with teammate's role-based frontend

**Your work:** Backend security features (hash chain, audit logs, Security page)
**Her work:** Frontend with 3 roles (Admin, Manager, User) and role-based dashboards

---

## 📋 Pre-Merge Checklist

### ✅ Before She Pushes

- [ ] Commit all your current changes
- [ ] Create backup branch
- [ ] Backup your Security.jsx page
- [ ] Document your backend changes

### ✅ After She Pushes

- [ ] Pull her frontend changes
- [ ] Copy your Security page to her frontend
- [ ] Merge routing and navigation
- [ ] Test role-based access
- [ ] Test security features

---

## 🎯 Step 1: Backup Your Work

**Run these commands NOW:**

```bash
# Navigate to project
cd c:\Users\bhavy\OneDrive\Desktop\MIC1\documind_ai

# Commit current state
git add -A
git commit -m "feat: Complete security implementation before merge"

# Create backup branch
git branch backup/security-implementation

# Push to remote
git push origin feature/sha256-security
git push origin backup/security-implementation
```

**Backup your Security page:**

```bash
# Create a backup folder
mkdir merge-backup
mkdir merge-backup\frontend-components

# Copy your Security page
copy frontend\src\pages\Security.jsx merge-backup\frontend-components\
```

---

## 🎯 Step 2: When She Pushes (Wait for Her)

She should push to a branch like `feature/role-based-ui`

**Her branch should include:**
- Frontend with 3 role-based dashboards
- Auth context with role checking
- Role-based navigation
- Login page with role selection

---

## 🎯 Step 3: Pull Her Changes

```bash
# Fetch her branch
git fetch origin

# Create a new branch for merge
git checkout -b feature/security-plus-roles

# Pull her frontend branch
git pull origin feature/role-based-ui

# Or merge her branch
git merge origin/feature/role-based-ui
```

**If there are conflicts in `frontend/`:**
- Accept her changes for most files
- We'll manually add your Security page

---

## 🎯 Step 4: Add Your Security Page

### 4.1 Copy Security Page

```bash
# Copy your Security.jsx from backup
copy merge-backup\frontend-components\Security.jsx frontend\src\pages\
```

### 4.2 Update App.jsx (Add Security Route)

**Location:** `frontend/src/App.jsx`

**Find her routes section** (probably looks like):
```jsx
<Route path="admin-dashboard" element={<AdminDashboard />} />
<Route path="manager-dashboard" element={<ManagerDashboard />} />
<Route path="user-dashboard" element={<UserDashboard />} />
```

**Add these lines:**

```jsx
// At the top with other imports
import Security from './pages/Security'

// In the routes section (inside <Route path="/" element={<Layout />}>)
<Route path="security" element={<Security />} />
```

### 4.3 Update Layout.jsx (Add Security Nav Item)

**Location:** `frontend/src/components/Layout.jsx`

**Find the navigation array** (probably looks like):
```jsx
const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Upload', href: '/upload', icon: Upload },
  // ... more items
]
```

**Add Shield icon import:**
```jsx
import {
  LayoutDashboard,
  Upload,
  Shield,  // ← Add this
  // ... other icons
} from 'lucide-react'
```

**Add Security nav item:**
```jsx
const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Upload', href: '/upload', icon: Upload },
  { name: 'Documents', href: '/documents', icon: FileText },
  // ... her other items
  
  // Add this for Admin role only:
  ...(user?.role === 'admin' ? [
    { name: 'Security', href: '/security', icon: Shield }
  ] : []),
]
```

**Alternative (if she has adminOnly flag):**
```jsx
{ 
  name: 'Security', 
  href: '/security', 
  icon: Shield,
  adminOnly: true 
}
```

---

## 🎯 Step 5: Role-Based Access Control

### Check Her Auth Context

**Location:** `frontend/src/context/AuthContext.jsx`

**Look for how she stores roles:**
```jsx
// Option 1: User object with role
const { user } = useAuth() // user.role = "admin" | "manager" | "user"

// Option 2: Separate role check
const { isAdmin, isManager, isUser } = useAuth()
```

### Protect Security Route (If Needed)

**In App.jsx:**
```jsx
import { RequireAdmin } from './components/RequireAdmin' // If she has this

<Route 
  path="security" 
  element={
    <RequireAdmin>
      <Security />
    </RequireAdmin>
  } 
/>
```

**Or create your own:**
```jsx
function AdminRoute({ children }) {
  const { user } = useAuth()
  
  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }
  
  return children
}

// Then use:
<Route 
  path="security" 
  element={
    <AdminRoute>
      <Security />
    </AdminRoute>
  } 
/>
```

---

## 🎯 Step 6: Update Backend for Roles

### 6.1 Update Auth to Include Role

**Location:** `back-end/auth/auth.py`

**Current:**
```python
class UserInfo(BaseModel):
    user_id: str
    email: str
```

**Update to:**
```python
class UserInfo(BaseModel):
    user_id: str
    email: str
    role: str = "user"  # "admin", "manager", "user"
```

### 6.2 Get Role from Supabase

**In `get_current_user()` function:**
```python
# Extract role from JWT or user metadata
role = payload.get("role", "user")  # Default to "user"

return UserInfo(
    user_id=user_id,
    email=email,
    role=role
)
```

### 6.3 Add Role-Based Route Protection

**Create decorator in `auth/auth.py`:**
```python
from functools import wraps
from fastapi import HTTPException, status

def require_role(allowed_roles: list):
    """Decorator to require specific roles."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user: UserInfo = Depends(get_current_user), **kwargs):
            if user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of: {allowed_roles}"
                )
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator
```

**Usage in security routes:**
```python
@router.get("/security/hash-chain/stats")
async def get_chain_stats(user: UserInfo = Depends(require_role(["admin"]))):
    # Only admin can access
    ...
```

---

## 🎯 Step 7: Test the Merged App

### 7.1 Start Backend
```bash
cd back-end
python -m uvicorn main:app --reload --port 8000
```

### 7.2 Start Frontend
```bash
cd frontend
npm install  # In case she has new dependencies
npm run dev
```

### 7.3 Test Scenarios

**Test 1: Admin Login**
- [ ] Login as Admin
- [ ] See Security nav item in sidebar
- [ ] Click Security → Page loads
- [ ] See hash chain stats
- [ ] See audit logs
- [ ] Upload document → Stats update

**Test 2: Manager Login**
- [ ] Login as Manager
- [ ] Should NOT see Security nav item
- [ ] Navigate to `/security` manually → Redirected to dashboard
- [ ] Can upload documents
- [ ] Can view documents

**Test 3: User Login**
- [ ] Login as User
- [ ] Should NOT see Security nav item
- [ ] Can upload own documents
- [ ] Can only see own documents

**Test 4: Security Features**
- [ ] Upload 3 documents (as different roles)
- [ ] Security page shows all 3 in hash chain
- [ ] Audit logs show all uploads with user roles
- [ ] Click "Verify Chain" → Shows valid
- [ ] Recent Activity shows all users

---

## 🎯 Step 8: Resolve Common Issues

### Issue 1: Security Page Not Showing

**Check:**
- Security.jsx copied to correct location?
- Route added to App.jsx?
- Icon imported in Layout.jsx?

**Fix:**
```bash
# Verify file exists
dir frontend\src\pages\Security.jsx

# Check App.jsx for Security import and route
```

### Issue 2: Navigation Not Showing Security

**Check her navigation logic:**
```jsx
// If she filters by role:
const filteredNav = navigation.filter(item => {
  if (item.adminOnly) return user.role === 'admin'
  return true
})
```

### Issue 3: API Calls Failing

**Check:**
- Backend is running on port 8000?
- Frontend .env has correct API URL?
- CORS configured for her frontend URL?

**Fix:**
```bash
# Check .env
type frontend\.env
# Should have: VITE_API_BASE_URL=http://localhost:8000

# Check backend CORS
# Should include: http://localhost:3000,http://localhost:5173
```

### Issue 4: Role Not Passed from Backend

**Update backend auth:**
- Make sure `UserInfo` has `role` field
- Make sure JWT includes role
- Test: `GET /users/me` should return role

---

## 🎯 Step 9: Final Commit

```bash
# Test everything works
# Then commit merged code

git add -A
git commit -m "feat: Merge security backend with role-based frontend

- Integrated Security page (admin only)
- Hash chain and audit logs working
- Role-based access control
- All 3 roles tested and working
"

# Push to remote
git push origin feature/security-plus-roles
```

---

## 📊 What Gets Merged

### Your Contributions (Keep)
- ✅ `back-end/security/` - All security modules
- ✅ `back-end/routes/security_routes.py` - Security API
- ✅ Hash chain integration in upload
- ✅ Audit logging
- ✅ Security page component

### Her Contributions (Keep)
- ✅ Role-based authentication
- ✅ 3 different dashboards
- ✅ Role-based navigation
- ✅ Better UI/UX
- ✅ Role selection on login

### Combined Result
- ✅ Backend with security + role support
- ✅ Frontend with 3 roles + Security page
- ✅ Admin can see Security page
- ✅ All roles can upload documents
- ✅ Hash chain tracks all documents
- ✅ Audit logs show user roles

---

## 🚨 Emergency Rollback

If merge fails badly:

```bash
# Restore from backup branch
git checkout backup/security-implementation

# Or reset to before merge
git reset --hard HEAD~1

# Restore frontend from backup
rmdir /s frontend
xcopy merge-backup\frontend frontend\ /E /I /H
```

---

## 📞 Communicate with Teammate

**Before Merge:**
"Hey! Ready to merge. Please push your role-based frontend to `feature/role-based-ui`. 
Include: AuthContext, role logic, and all 3 dashboards."

**During Merge:**
"Merging now. I'm adding Security page as admin-only. 
Will test all 3 roles and security features."

**After Merge:**
"Merge complete! Testing:
- ✅ Admin sees Security page
- ✅ Hash chain working
- ✅ Audit logs working
- ✅ All roles functional

Please test on your end!"

---

## ✅ Success Criteria

Merge is successful when:
- [ ] Backend starts without errors
- [ ] Frontend builds without errors
- [ ] All 3 roles can login
- [ ] Admin sees Security page
- [ ] Manager/User don't see Security page
- [ ] Documents upload successfully
- [ ] Hash chain updates correctly
- [ ] Audit logs track all users
- [ ] Navigation works for all roles
- [ ] No console errors

---

## 📚 Files to Review Together

After merge, review these with her:
1. `frontend/src/App.jsx` - Route structure
2. `frontend/src/components/Layout.jsx` - Navigation logic
3. `frontend/src/context/AuthContext.jsx` - Role management
4. `back-end/auth/auth.py` - Backend role support

---

## 🎉 Post-Merge

Once successful:
1. Demo to team/instructor
2. Document the architecture
3. Plan next features:
   - Role-specific security dashboards?
   - Manager can view team's audit logs?
   - User can see own audit trail?

Good luck with the merge! 🚀
